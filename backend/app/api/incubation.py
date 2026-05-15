from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import httpx
import time
import json
import logging
from app.core.config import settings
from app.core.dependencies import get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()

DRIFT_PIPELINE_ID = "6a06a1094e965b488e905711"
DRIFT_LLM_URL = f"https://driftllm.cisco.com/pipelines/llm/{DRIFT_PIPELINE_ID}"
CISCO_TOKEN_URL = "https://id.cisco.com/oauth2/default/v1/token"

# Module-level token cache (per-process)
_token_cache: Dict[str, Any] = {"token": None, "expires_at": 0.0}


def _get_cisco_token() -> str:
    current_time = time.time()
    if _token_cache["token"] and current_time < _token_cache["expires_at"]:
        return _token_cache["token"]

    try:
        response = httpx.post(
            CISCO_TOKEN_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "client_credentials",
                "client_id": settings.DRIFT_CLIENT_ID,
                "client_secret": settings.DRIFT_CLIENT_SECRET,
            },
            timeout=10.0,
        )
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Token request failed: {exc}")

    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to obtain Cisco token ({response.status_code})",
        )

    data = response.json()
    token = data.get("access_token")
    if not token:
        raise HTTPException(status_code=502, detail="No access_token in Cisco response")

    expires_in = data.get("expires_in", 3600)
    _token_cache["token"] = token
    _token_cache["expires_at"] = current_time + expires_in - 300  # 5-min buffer
    return token


class IncubationSearchRequest(BaseModel):
    query: str
    meta_filters: Optional[Dict[str, Any]] = None


class SourceDoc(BaseModel):
    content: Optional[str] = None
    score: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class IncubationSearchResponse(BaseModel):
    answer: str
    sources: List[SourceDoc] = []


def _parse_sources(raw: Any) -> List[SourceDoc]:
    """Normalise whatever DRIFT returns into a flat list of SourceDoc."""
    if not raw:
        return []
    if isinstance(raw, list):
        result = []
        for item in raw:
            if isinstance(item, dict):
                result.append(
                    SourceDoc(
                        content=item.get("content") or item.get("text") or item.get("page_content"),
                        score=item.get("score") or item.get("reranker_score"),
                        metadata=item.get("metadata") or {k: v for k, v in item.items() if k not in ("content", "text", "page_content", "score", "reranker_score")},
                    )
                )
        return result
    return []


@router.post("/search", response_model=IncubationSearchResponse)
async def incubation_search(
    request: IncubationSearchRequest,
    current_user: User = Depends(get_current_user),
):
    token = _get_cisco_token()

    # search_params must be a JSON string per the DRIFT API spec
    search_params = json.dumps([
        {"search_strategy": "ensemble", "k": 10, "weight": 0.5},
        {"search_strategy": "keyword", "k": 10, "weight": 0.5},
        {"search_strategy": "semantic", "k": 10, "weight": 0.5},
    ])

    payload: Dict[str, Any] = {
        "query": request.query,
        "user": current_user.email,
        "search_params": search_params,
        "reranker_model": "Granite",
        "k": 5,
        "min_score": 0.5,
    }

    if request.meta_filters:
        payload["meta_filters"] = request.meta_filters

    headers = {
        "Content-Type": "application/json",
        "client": settings.DRIFT_CLIENT_ID,
        "Authorization": f"Bearer {token}",
    }

    logger.info(f"DRIFT search: user={current_user.email} query={request.query[:80]}")

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(DRIFT_LLM_URL, json=payload, headers=headers)
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="DRIFT API request timed out")
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"DRIFT API unreachable: {exc}")

    if resp.status_code != 200:
        logger.error(f"DRIFT API error {resp.status_code}: {resp.text[:500]}")
        raise HTTPException(
            status_code=resp.status_code,
            detail=f"DRIFT API returned {resp.status_code}: {resp.text[:200]}",
        )

    try:
        data = resp.json()
    except Exception:
        raise HTTPException(status_code=502, detail="DRIFT API returned non-JSON response")

    # Extract answer — try multiple common keys
    answer = (
        data.get("answer")
        or data.get("response")
        or data.get("result")
        or data.get("text")
        or str(data)
    )

    # Extract sources — try multiple common keys
    raw_sources = (
        data.get("sources")
        or data.get("documents")
        or data.get("chunks")
        or data.get("context")
        or []
    )

    return IncubationSearchResponse(
        answer=answer,
        sources=_parse_sources(raw_sources),
    )
