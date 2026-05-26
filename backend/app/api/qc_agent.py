from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Union, Dict, Any
import httpx
import base64
import time
import json
import re
import logging
import asyncio
import uuid
from app.core.config import settings
from app.core.dependencies import get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()

CISCO_TOKEN_URL = "https://id.cisco.com/oauth2/default/v1/token"
QC_RAG_URL = "https://chat-ai.cisco.com/genai-ext-rag/api/v2.0/context_inference"

# Module-level token cache (per-process)
_token_cache: Dict[str, Any] = {"token": None, "expires_at": 0.0}


def _get_qc_token() -> str:
    current_time = time.time()
    if _token_cache["token"] and current_time < _token_cache["expires_at"]:
        return _token_cache["token"]

    credentials = f"{settings.QC_CLIENT_ID}:{settings.QC_CLIENT_SECRET}"
    encoded = base64.b64encode(credentials.encode()).decode()

    try:
        response = httpx.post(
            CISCO_TOKEN_URL,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"Basic {encoded}",
            },
            data={"grant_type": "client_credentials"},
            timeout=15.0,
        )
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Token request failed: {exc}")

    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to obtain Cisco token ({response.status_code}): {response.text}",
        )

    data = response.json()
    token = data.get("access_token")
    if not token:
        raise HTTPException(status_code=502, detail="No access_token in Cisco response")

    expires_in = data.get("expires_in", 3600)
    _token_cache["token"] = token
    _token_cache["expires_at"] = current_time + expires_in - 300  # 5-min buffer
    return token


class QCQueryRequest(BaseModel):
    query: str
    selected_sources: Optional[Union[str, List[str]]] = "CDC"
    additional_filters: Optional[Dict[str, Any]] = None
    chat_conversation_id: Optional[str] = ""
    chat_session_id: Optional[str] = ""


class QCQueryResponse(BaseModel):
    answer: str
    original_query: str
    sources: List[Dict[str, Any]]
    session_id: Optional[str] = None
    is_answer_unknown: bool = False
    return_code: int = 0
    return_message: str = "Success"
    conversation_title: Optional[str] = None


@router.post("/query", response_model=QCQueryResponse)
async def qc_agent_query(
    request: QCQueryRequest,
    current_user: User = Depends(get_current_user),
):
    if not settings.QC_CLIENT_ID or not settings.QC_CLIENT_SECRET or not settings.QC_APP_ID:
        raise HTTPException(
            status_code=503,
            detail="QC Agent is not configured. Missing credentials.",
        )

    token = _get_qc_token()

    payload: Dict[str, Any] = {
        "UserID": current_user.email or "agent-qcagent",
        "Query": request.query,
        "AppId": settings.QC_APP_ID,
        "chatConversationID": request.chat_conversation_id or "",
        "chatRequestID": "",
        "chatSessionID": request.chat_session_id or "",
        "SelectedSources": request.selected_sources or "CDC",
        "Streaming": False,
        "HistoryWrite": False,
    }

    if request.additional_filters:
        payload["AdditionalFilters"] = request.additional_filters

    try:
        response = httpx.post(
            QC_RAG_URL,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
            json=payload,
            timeout=60.0,
        )
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"RAG API request failed: {exc}")

    if response.status_code == 401:
        # Token may have expired mid-cache window — invalidate and surface error
        _token_cache["token"] = None
        _token_cache["expires_at"] = 0.0
        raise HTTPException(status_code=502, detail="Cisco RAG authorization failed. Token invalidated — retry.")

    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Cisco RAG API error ({response.status_code}): {response.text}",
        )

    data = response.json()

    # Extract is_answer_unknown from meta array
    is_unknown = False
    meta = data.get("meta", [])
    if isinstance(meta, list) and meta:
        is_unknown = meta[0].get("is_answer_unknown", False)

    return QCQueryResponse(
        answer=data.get("data", ""),
        original_query=data.get("ogQuery", request.query),
        sources=meta,
        session_id=data.get("session_id"),
        is_answer_unknown=is_unknown,
        return_code=data.get("return_code", 0),
        return_message=data.get("return_message", "Success"),
        conversation_title=data.get("chat_conversation_title"),
    )


# ═══════════════════════════════════════════════════════════════════════════
# Content Validation Endpoint (JSON Training Content QC)
# ═══════════════════════════════════════════════════════════════════════════

class ContentValidationRequest(BaseModel):
    json_content: str
    module_name: Optional[str] = None
    selected_sources: Optional[Union[str, List[str]]] = "CDC"
    product_override: Optional[str] = None  # explicit product/solution filter (overrides auto-detected)


class ValidationFinding(BaseModel):
    claim: str
    status: str  # "validated", "needs_revision", "inaccurate", "unverified"
    exact_quote: Optional[str] = None
    cisco_answer: Optional[str] = None
    sources: List[Dict[str, Any]] = []


class ContentValidationResponse(BaseModel):
    module_name: str
    is_truncated: bool
    extracted_claims: List[str]
    validation_findings: List[ValidationFinding]
    qc_report: str  # Full 7-section markdown report
    validated_count: int
    flagged_count: int


class ValidationJobResponse(BaseModel):
    job_id: str
    status: str  # processing | complete | error
    progress: int = 0
    total: int = 0
    module_name: str = "Processing..."
    result: Optional[ContentValidationResponse] = None
    error: Optional[str] = None


# ─── In-memory job store (per-process) ───────────────────────────────────────
_jobs: Dict[str, Dict[str, Any]] = {}


async def _call_rag_api(query: str, user_email: str, max_retries: int = 3, product_filter: Optional[str] = None) -> Dict[str, Any]:
    """Helper to call Cisco RAG API asynchronously with retry logic for rate limits"""
    import asyncio
    
    for attempt in range(max_retries):
        token = _get_qc_token()
        
        payload: Dict[str, Any] = {
            "UserID": user_email or "agent-qcagent",
            "Query": query,
            "AppId": settings.QC_APP_ID,
            "chatConversationID": "",
            "chatRequestID": "",
            "chatSessionID": "",
            "SelectedSources": "CDC",
            "Streaming": False,
            "HistoryWrite": False,
        }

        # Attempt product-level filtering via AdditionalFilters.
        # Cisco CDC indexes products under their short name (without "Cisco " prefix).
        # Strip the prefix so "Cisco Security Cloud Control" → "Security Cloud Control".
        if product_filter:
            short_name = product_filter.removeprefix("Cisco ").strip()
            payload["AdditionalFilters"] = {"product_families": [short_name]}
            logger.debug(f"RAG product filter applied: {short_name}")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    QC_RAG_URL,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {token}",
                    },
                    json=payload,
                    timeout=60.0,
                )
        except httpx.RequestError as exc:
            logger.error(f"RAG API request failed: {exc}")
            return {"answer": f"[Network Error: {str(exc)}]", "sources": [], "is_unknown": True, "error": True}

        # Handle rate limiting with exponential backoff
        if response.status_code == 429:
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) * 1.5  # 1.5s, 3s, 6s
                logger.warning(f"RAG API rate limit hit (429), retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(wait_time)
                continue
            else:
                logger.error(f"RAG API rate limit exceeded after {max_retries} attempts")
                return {"answer": "[Rate Limit Exceeded - Cisco API rejected request after multiple retries]", "sources": [], "is_unknown": True, "error": True}

        if response.status_code != 200:
            logger.error(f"RAG API error {response.status_code}: {response.text}")
            return {"answer": f"[API Error {response.status_code}]", "sources": [], "is_unknown": True, "error": True}

        data = response.json()
        meta = data.get("meta", [])
        is_unknown = False
        if isinstance(meta, list) and meta:
            is_unknown = meta[0].get("is_answer_unknown", False)

        return {
            "answer": data.get("data", ""),
            "sources": meta,
            "is_unknown": is_unknown,
            "error": False,
        }
    
    return {"answer": "[Max retries exceeded]", "sources": [], "is_unknown": True, "error": True}


@router.post("/validate-content", response_model=ValidationJobResponse)
async def validate_training_content(
    request: ContentValidationRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Starts a background QC validation job. Returns a job_id immediately.
    Poll GET /validate-content/status/{job_id} for progress and results.
    """
    if not settings.QC_CLIENT_ID or not settings.QC_CLIENT_SECRET or not settings.QC_APP_ID:
        raise HTTPException(
            status_code=503,
            detail="QC Agent is not configured. Missing credentials.",
        )

    # Fast pre-validation: parse JSON before starting background task
    clean_content = re.sub(r'^```json\s*', '', request.json_content, flags=re.M)
    clean_content = re.sub(r'```\s*$', '', clean_content, flags=re.M)
    clean_content = clean_content.strip()

    try:
        parsed_data = json.loads(clean_content)
        if not isinstance(parsed_data, dict):
            raise ValueError("Parsed JSON is not a dictionary")
    except (ValueError, json.JSONDecodeError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON content: {str(e)}")

    module_name = (
        request.module_name or
        parsed_data.get('module') or
        parsed_data.get('moduleName') or
        parsed_data.get('module_name') or
        parsed_data.get('title') or
        parsed_data.get('name') or
        parsed_data.get('topic') or
        parsed_data.get('subject') or
        "Unknown Module"
    )

    # Clean up old jobs (older than 2 hours) to prevent memory leaks
    cutoff = time.time() - 7200
    for old_id in [k for k, v in _jobs.items() if v.get("created_at", 0) < cutoff]:
        _jobs.pop(old_id, None)

    # Create job entry and launch background task
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {
        "status": "processing",
        "progress": 0,
        "total": 0,
        "module_name": module_name,
        "result": None,
        "error": None,
        "created_at": time.time(),
    }

    asyncio.create_task(_run_validation(job_id, clean_content, parsed_data, module_name, request, current_user))
    logger.info(f"QC job {job_id} started for module: {module_name}")

    return ValidationJobResponse(
        job_id=job_id,
        status="processing",
        module_name=module_name,
    )


@router.get("/validate-content/status/{job_id}", response_model=ValidationJobResponse)
async def get_validation_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
):
    """Poll this endpoint every 3-5 seconds to get job progress and final result."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or expired")

    return ValidationJobResponse(
        job_id=job_id,
        status=job["status"],
        progress=job["progress"],
        total=job["total"],
        module_name=job["module_name"],
        result=job["result"],
        error=job["error"],
    )


async def _run_validation(
    job_id: str,
    clean_content: str,
    parsed_data: dict,
    module_name: str,
    request: ContentValidationRequest,
    current_user: User,
):
    """Background task: extract claims, validate all, build report, store result."""
    try:
        is_truncated = len(clean_content) < 100 or not clean_content.endswith('}')

        # ─── Derive product context from fullname ─────────────────────────
        # fullname pattern: "Product Family - Feature Name (Acronym)"
        # Extract the product family (everything before the first " - ")
        raw_fullname = parsed_data.get('fullname', module_name)
        product_context = raw_fullname.split(' - ')[0].strip() if ' - ' in raw_fullname else raw_fullname
        # Allow caller to override the auto-detected product context
        if request.product_override and request.product_override.strip():
            product_context = request.product_override.strip()
        logger.info(f"[Job {job_id}] Product context: {product_context}")

        # ─── Extract Claims ───────────────────────────────────────────────
        logger.info(f"[Job {job_id}] Extracting claims for: {module_name}")

        def _strip_html(s: str) -> str:
            return re.sub(r'<[^>]+>', '', s).strip()

        def _extract_claims_from_schema(data: dict) -> List[str]:
            """
            Schema-aware claim extractor — universal quality filtering, no caps.

            Universal rules (apply to any module regardless of size):
              1. Skip section-0 pages  (course intro / navigation menus)
              2. Skip any item ending with '?'  (discovery / objection questions)
              3. Minimum 80 chars after HTML strip  (removes short bullets & metadata)
                 Exception: quiz answers only need 30 chars (they are complete choices)
              4. Deduplicate by first 120 chars, case-insensitive

            Result scales naturally: small modules → fewer claims,
            large modules → more claims. No arbitrary caps.
            """
            seen: set = set()
            results: List[str] = []

            def add(raw: str, min_len: int = 80) -> None:
                clean = _strip_html(raw).strip()
                if len(clean) < min_len:
                    return
                if clean.rstrip().endswith('?'):
                    return
                key = clean[:80].lower()
                if key not in seen:
                    seen.add(key)
                    results.append(clean)

            for page in data.get('pages', []):
                if page.get('section', -1) == 0:   # skip intro/navigation page
                    continue
                for block in page.get('content', []):
                    t = block.get('type', '')
                    if t == 'paragraph':
                        add(block.get('text', ''))
                    elif t == 'list':
                        for li in block.get('items', []):
                            if isinstance(li, str):
                                add(li)
                    elif t == 'callout':
                        add(block.get('content', ''))
                    elif t == 'table':
                        headers = block.get('headers', [])
                        for row in block.get('rows', []):
                            if not isinstance(row, list):
                                continue
                            for i, cell in enumerate(row):
                                if not isinstance(cell, str):
                                    continue
                                label = headers[i] if i < len(headers) else ''
                                claim_text = f"{label}: {cell}" if label else cell
                                add(claim_text)
                    elif t == 'card':
                        add(block.get('content', ''))

            for quiz in data.get('quizzes', []):
                for q in quiz.get('questions', []):
                    choices = q.get('choices', [])
                    idx = q.get('correctanswer', -1)
                    if 0 <= idx < len(choices):
                        add(choices[idx], min_len=30)

            return results

        # Try schema-based extraction first
        claims = _extract_claims_from_schema(parsed_data)

        # Fallback to RAG-based extraction if schema yields nothing
        # (handles non-standard JSON formats)
        if len(claims) < 5:
            logger.info(f"[Job {job_id}] Schema extraction yielded {len(claims)} claims, falling back to RAG extraction")
            content_excerpt = '\n'.join(
                v for v in (str(x) for x in parsed_data.values() if isinstance(x, str))
                if len(v) > 20
            )[:20000] or clean_content[:20000]

            extraction_query = f"""Extract all explicit technical claims, feature capabilities, configurations, version requirements, and procedural statements from the following training content.

Output ONLY a numbered list of claims, one per line. Be specific and quote exact technical details. Do not add commentary or analysis.

Training Content:
{content_excerpt}"""

            extraction_result = await _call_rag_api(extraction_query, current_user.email)
            claims_text = extraction_result['answer']
            claims = [
                line.strip().lstrip('0123456789.-) ').strip()
                for line in claims_text.split('\n')
                if line.strip() and any(c.isalnum() for c in line)
            ]
            claims = [c for c in claims if len(c) > 60]
            await asyncio.sleep(1.0)  # clear rate-limit burst window after extraction call
        else:
            logger.info(f"[Job {job_id}] Schema extraction found {len(claims)} claims (no RAG call needed)")

        _jobs[job_id]["total"] = len(claims)
        logger.info(f"[Job {job_id}] {len(claims)} claims ready for validation")
        semaphore = asyncio.Semaphore(6)

        async def validate_single_claim(claim: str, index: int) -> ValidationFinding:
            async with semaphore:
                start_time = time.time()
                logger.info(f"[Job {job_id}] Validating claim {index + 1}/{len(claims)}: {claim[:60]}...")

                validation_query = f"""You are validating training content about {product_context}.

Statement to validate: {claim}

Instructions:
- Only use {product_context} documentation to validate this statement.
- Do NOT reference documentation from other Cisco products (e.g. Catalyst, MDS, Wireless, Cyber Vision, or unrelated platforms) even if retrieved.
- If you cannot find relevant {product_context} documentation, use VERDICT: NEEDS_REVISION.

Begin your response with exactly one of these verdict labels on the first line:
VERDICT: ACCURATE
VERDICT: INACCURATE
VERDICT: NEEDS_REVISION

Use ACCURATE if the statement is correct and complete per {product_context} documentation.
Use INACCURATE if the statement contains factual errors or contradicts {product_context} documentation.
Use NEEDS_REVISION if the statement is partially correct but missing important caveats, version constraints, or prerequisites.

Then explain your reasoning with specific details from {product_context} documentation."""

                rag_result = await _call_rag_api(validation_query, current_user.email, product_filter=product_context)

                elapsed = time.time() - start_time
                logger.info(f"[Job {job_id}] Claim {index + 1} done in {elapsed:.1f}s")

                # Update progress counter
                _jobs[job_id]["progress"] = _jobs[job_id].get("progress", 0) + 1

                if rag_result.get('error'):
                    status = "needs_revision"
                    cisco_answer = rag_result['answer']
                else:
                    answer = rag_result['answer']
                    is_unknown = rag_result['is_unknown']

                    # Detect Cisco system error responses served as HTTP 200
                    # (e.g. "Apologies for the inconvenience...temporary technical issue")
                    _CISCO_ERROR_PHRASES = [
                        "apologies for the inconvenience",
                        "temporary technical issue",
                        "try again shortly",
                        "system is currently experiencing",
                    ]
                    if any(p in answer.lower() for p in _CISCO_ERROR_PHRASES):
                        status = "unverified"
                        cisco_answer = "[API temporarily unavailable — could not be verified. Please re-run.]"
                    elif is_unknown or not answer.strip():
                        status = "needs_revision"
                        cisco_answer = answer
                    else:
                        # Strip the VERDICT line from the displayed answer
                        answer_lines = answer.strip().split('\n')
                        if answer_lines and answer_lines[0].upper().startswith('VERDICT:'):
                            cisco_answer = '\n'.join(answer_lines[1:]).strip()
                        else:
                            cisco_answer = answer

                        # Parse the explicit verdict from the first line
                        first_line = answer.strip().split('\n')[0].upper()
                        if 'VERDICT: INACCURATE' in first_line or 'INACCURATE' in first_line:
                            status = "inaccurate"
                        elif 'VERDICT: NEEDS_REVISION' in first_line or 'NEEDS_REVISION' in first_line or 'NEEDS REVISION' in first_line:
                            status = "needs_revision"
                        elif 'VERDICT: ACCURATE' in first_line or first_line.startswith('ACCURATE'):
                            status = "validated"
                        else:
                            # Fallback: scan for explicit negative phrases only
                            answer_lower = answer.lower()
                            if any(phrase in answer_lower for phrase in [
                                "this statement is inaccurate",
                                "this claim is inaccurate",
                                "this is incorrect",
                                "this statement is incorrect",
                                "this is inaccurate",
                                "factually incorrect",
                                "factually inaccurate",
                            ]):
                                status = "inaccurate"
                            elif any(phrase in answer_lower for phrase in [
                                "partially accurate",
                                "partially correct",
                                "missing important",
                                "should note that",
                                "this statement is accurate but",
                                "accurate, but",
                                "accurate with some",
                            ]):
                                status = "needs_revision"
                            else:
                                status = "validated"

                return ValidationFinding(
                    claim=claim,
                    status=status,
                    exact_quote=None,
                    cisco_answer=cisco_answer,
                    sources=rag_result['sources']
                )

        validation_start = time.time()
        tasks = [validate_single_claim(claim, idx) for idx, claim in enumerate(claims)]
        logger.info(f"[Job {job_id}] Launching {len(tasks)} tasks (max 6 concurrent)...")
        findings = await asyncio.gather(*tasks)
        validation_elapsed = time.time() - validation_start
        logger.info(f"[Job {job_id}] All {len(findings)} claims validated in {validation_elapsed:.1f}s")

        validated_count  = sum(1 for f in findings if f.status == "validated")
        flagged_count   = sum(1 for f in findings if f.status in ("needs_revision", "inaccurate"))
        unverified_count = sum(1 for f in findings if f.status == "unverified")

        # ─── Build 7-Section QC Report ────────────────────────────────────
        report_sections = []

        report_sections.append(
            f"## 🛡️ Cisco Content Quality Check Report\n\n"
            f"**Module:** {module_name}\n\n"
            f"**Validation Date:** {time.strftime('%Y-%m-%d %H:%M UTC')}\n\n"
            f"Greetings, Knowledge Guardian! Your training module on **{module_name}** has been validated against authoritative Cisco documentation. Here's what the QC sweep uncovered:\n"
        )

        report_sections.append(
            f"## 📋 Content Summary\n\n"
            f"This module contains **{len(claims)} technical claims** covering features, configurations, and operational procedures. "
            f"**{validated_count}** confirmed accurate · **{flagged_count}** flagged for revision · **{unverified_count}** could not be verified (API unavailable).\n"
        )

        validation_results = ["## 🔎 Validation Results\n"]
        for idx, finding in enumerate(findings, 1):
            if finding.status == "validated":
                icon, label = "✅", "Accurate"
            elif finding.status == "inaccurate":
                icon, label = "❌", "Inaccurate"
            elif finding.status == "unverified":
                icon, label = "🔄", "Could Not Verify"
            else:
                icon, label = "⚠️", "Needs Revision"

            validation_results.append(f"\n### {icon} Claim {idx}: {label}\n")
            validation_results.append(f"**Statement:** \"{finding.claim}\"\n")
            if finding.cisco_answer and not finding.cisco_answer.startswith('['):
                validation_results.append(f"\n**Cisco Documentation Review:**\n{finding.cisco_answer}\n")
            elif finding.cisco_answer:
                validation_results.append(f"\n**Issue:** {finding.cisco_answer}\n")
        report_sections.append('\n'.join(validation_results))

        edits = ["## ✏️ Suggested Edits\n"]
        has_edits = False
        for idx, finding in enumerate(findings, 1):
            if finding.status not in ("validated", "unverified"):
                has_edits = True
                edits.append(f"\n**Claim {idx}:** \"{finding.claim[:100]}{'...' if len(finding.claim) > 100 else ''}\"\n")
                if finding.status == "needs_revision":
                    edits.append("**Issue:** Cisco documentation does not clearly confirm this claim.\n")
                    edits.append(f"**Cisco Documentation Says:** {finding.cisco_answer[:400]}{'...' if len(finding.cisco_answer or '') > 400 else ''}\n")
                    edits.append("**Recommendation:** Revise to align with authoritative Cisco documentation, or remove if unsupported.\n")
                else:
                    edits.append("**Issue:** This claim appears to be inaccurate or outdated.\n")
                    edits.append(f"**Cisco Documentation Says:** {finding.cisco_answer[:400]}{'...' if len(finding.cisco_answer or '') > 400 else ''}\n")
                    edits.append("**Recommendation:** Correct this statement to match current Cisco documentation.\n")
        if not has_edits:
            edits.append("\n*No edits required — all validated claims align with Cisco documentation.*\n")
        report_sections.append('\n'.join(edits))

        gaps = ["## 🔍 Coverage Gaps\n"]
        gaps.append("\n*Note: Comprehensive gap analysis requires subject matter expert review. Consider adding sections on:*\n")
        gaps.append("- Prerequisites and version compatibility\n")
        gaps.append("- High availability and failover considerations\n")
        gaps.append("- Integration points with other Cisco products\n")
        gaps.append("- Common troubleshooting scenarios\n")
        report_sections.append('\n'.join(gaps))

        audience = ["## 👥 Audience Fit Assessment\n"]
        reviewable = len(findings) - unverified_count
        audience.append(f"\nThis training content is {'highly appropriate' if validated_count > flagged_count else 'partially suitable'} for Cisco Systems Engineers. ")
        audience.append(f"Of **{reviewable} verifiable claims**, **{validated_count}** are confirmed accurate and **{flagged_count}** need revision. ")
        if unverified_count > 0:
            audience.append(f"**{unverified_count} claim(s)** could not be verified due to a temporary API outage — re-run to complete the review. ")
        if flagged_count > 0:
            audience.append(f"\n\n**Recommendation:** Address the **{flagged_count} flagged items** before deployment to ensure field-ready accuracy.\n")
        else:
            audience.append("\n\nThe content is deployment-ready for SE enablement.\n")
        report_sections.append('\n'.join(audience))

        qc_report = '\n\n'.join(report_sections)
        if is_truncated:
            qc_report += "\n\n⚠️ **Note:** The provided JSON appeared truncated. This report reflects only the data successfully parsed.\n"

        result = ContentValidationResponse(
            module_name=module_name,
            is_truncated=is_truncated,
            extracted_claims=claims,
            validation_findings=findings,
            qc_report=qc_report,
            validated_count=validated_count,
            flagged_count=flagged_count,
        )

        _jobs[job_id]["status"] = "complete"
        _jobs[job_id]["result"] = result
        logger.info(f"[Job {job_id}] Complete: {validated_count} validated, {flagged_count} flagged")

    except Exception as e:
        logger.error(f"[Job {job_id}] Failed: {e}", exc_info=True)
        _jobs[job_id]["status"] = "error"
        _jobs[job_id]["error"] = str(e)

        raise HTTPException(
            status_code=503,
            detail="QC Agent is not configured. Missing credentials.",
        )

    # ─── 1. Parse JSON ───────────────────────────────────────────────────────
    logger.info(f"Content validation requested by {current_user.email}")
