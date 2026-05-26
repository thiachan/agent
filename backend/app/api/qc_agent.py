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


class ValidationFinding(BaseModel):
    claim: str
    status: str  # "validated", "needs_revision", "inaccurate"
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


async def _call_rag_api(query: str, user_email: str, max_retries: int = 3) -> Dict[str, Any]:
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

        # ─── Extract Claims ───────────────────────────────────────────────
        logger.info(f"[Job {job_id}] Extracting claims for: {module_name}")

        # Walk the full JSON tree to extract all text, regardless of nesting depth
        def _extract_text(obj: Any, depth: int = 0) -> List[str]:
            if depth > 10:
                return []
            if isinstance(obj, str) and len(obj.strip()) > 15:
                return [obj.strip()]
            if isinstance(obj, dict):
                return [t for v in obj.values() for t in _extract_text(v, depth + 1)]
            if isinstance(obj, list):
                return [t for item in obj for t in _extract_text(item, depth + 1)]
            return []

        all_text = _extract_text(parsed_data)
        full_text = '\n'.join(all_text)
        # Use up to 20000 chars — enough for very large modules
        content_excerpt = full_text[:20000] if len(full_text) > 0 else clean_content[:20000]
        logger.info(f"[Job {job_id}] Content text length: {len(content_excerpt)} chars from {len(all_text)} text nodes")

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
        claims = [c for c in claims if len(c) > 20]

        _jobs[job_id]["total"] = len(claims)
        logger.info(f"[Job {job_id}] Extracted {len(claims)} claims")

        # Small delay after extraction to clear rate limit burst window
        await asyncio.sleep(1.0)

        # ─── Validate ALL Claims (rate-limited concurrency) ───────────────
        semaphore = asyncio.Semaphore(6)

        async def validate_single_claim(claim: str, index: int) -> ValidationFinding:
            async with semaphore:
                start_time = time.time()
                logger.info(f"[Job {job_id}] Validating claim {index + 1}/{len(claims)}: {claim[:60]}...")

                validation_query = f"""Review the following statement against Cisco documentation.

Statement: {claim}

Begin your response with exactly one of these verdict labels on the first line:
VERDICT: ACCURATE
VERDICT: INACCURATE
VERDICT: NEEDS_REVISION

Use ACCURATE if the statement is correct and complete.
Use INACCURATE if the statement contains factual errors or contradicts Cisco documentation.
Use NEEDS_REVISION if the statement is partially correct but missing important caveats, version constraints, or prerequisites.

Then on the next lines, explain your reasoning and provide the correct Cisco documentation details."""

                rag_result = await _call_rag_api(validation_query, current_user.email)

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
                    # Strip the VERDICT line from the displayed answer so the report reads cleanly
                    answer_lines = answer.strip().split('\n')
                    if answer_lines and answer_lines[0].upper().startswith('VERDICT:'):
                        cisco_answer = '\n'.join(answer_lines[1:]).strip()
                    else:
                        cisco_answer = answer

                    if is_unknown or not answer.strip():
                        status = "needs_revision"
                    else:
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
                            # Only flag as inaccurate if it very explicitly says so
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

        validated_count = sum(1 for f in findings if f.status == "validated")
        flagged_count = sum(1 for f in findings if f.status != "validated")

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
            f"**{validated_count} claims** were validated against Cisco documentation, while **{flagged_count} claims** require revision or lack authoritative sources.\n"
        )

        validation_results = ["## 🔎 Validation Results\n"]
        for idx, finding in enumerate(findings, 1):
            if finding.status == "validated":
                icon, label = "✅", "Accurate"
            elif finding.status == "inaccurate":
                icon, label = "❌", "Inaccurate"
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
            if finding.status != "validated":
                has_edits = True
                edits.append(f"\n**Claim {idx}:** \"{finding.claim[:100]}{'...' if len(finding.claim) > 100 else ''}\"\n")
                if finding.cisco_answer and finding.cisco_answer.startswith('['):
                    edits.append(f"**Issue:** {finding.cisco_answer}\n")
                    edits.append("**Recommendation:** Unable to validate due to API error. Please retry or verify manually.\n")
                elif finding.status == "needs_revision":
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
        audience.append(f"\nThis training content is {'highly appropriate' if validated_count > flagged_count else 'partially suitable'} for Cisco Systems Engineers. ")
        audience.append(f"With **{validated_count} validated claims** out of **{len(findings)} reviewed**, the technical accuracy is {'strong' if validated_count > flagged_count else 'moderate'}. ")
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
