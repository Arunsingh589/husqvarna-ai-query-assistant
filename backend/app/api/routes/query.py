import logging
import time
from dataclasses import asdict

from fastapi import APIRouter, Depends, Request

from app.api.dependencies import CurrentSubject, LLMProviderDep, enforce_rate_limit
from app.schemas import ErrorResponse, QueryRequest, QueryResponse, UsageOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["query"])

_ERROR_RESPONSES: dict[int | str, dict[str, object]] = {
    code: {"model": ErrorResponse} for code in (400, 401, 422, 429, 500, 502, 503, 504)
}


@router.post(
    "/query",
    response_model=QueryResponse,
    responses=_ERROR_RESPONSES,
    dependencies=[Depends(enforce_rate_limit)],
)
async def query(
    payload: QueryRequest,
    request: Request,
    subject: CurrentSubject,
    llm: LLMProviderDep,
) -> QueryResponse:
    started = time.perf_counter()
    result = await llm.complete(payload.query)

    logger.info(
        "LLM query ok user=%s query_chars=%d model=%s tokens=%s truncated=%s duration_ms=%d",
        subject,
        len(payload.query),
        result.model,
        result.usage.total_tokens if result.usage else "n/a",
        result.truncated,
        (time.perf_counter() - started) * 1000,
    )

    return QueryResponse(
        answer=result.answer,
        model=result.model,
        truncated=result.truncated,
        usage=UsageOut(**asdict(result.usage)) if result.usage else None,
        request_id=request.state.request_id,
    )
