import logging
from collections.abc import Mapping
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class AppError(Exception):
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    code: str = "INTERNAL_ERROR"
    message: str = "An unexpected error occurred."

    def __init__(self, message: str | None = None, *, headers: dict[str, str] | None = None):
        super().__init__(message or self.message)
        self.message = message or self.message
        self.headers = headers


class AuthenticationError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "UNAUTHORIZED"
    message = "Missing or invalid authentication token."

    def __init__(self, message: str | None = None):
        super().__init__(message, headers={"WWW-Authenticate": "Bearer"})


class RateLimitExceededError(AppError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    code = "RATE_LIMITED"
    message = "Too many requests. Please slow down and try again shortly."

    def __init__(self, retry_after_seconds: int):
        super().__init__(headers={"Retry-After": str(retry_after_seconds)})


class LLMError(AppError):
    status_code = status.HTTP_502_BAD_GATEWAY
    code = "LLM_ERROR"
    message = "The AI service failed to process the request. Please try again."


class LLMTimeoutError(LLMError):
    status_code = status.HTTP_504_GATEWAY_TIMEOUT
    code = "LLM_TIMEOUT"
    message = "The AI service took too long to respond. Please try again."


class LLMUnavailableError(LLMError):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = "LLM_UNAVAILABLE"
    message = "The AI service is busy or unavailable. Please try again shortly."


class LLMContentBlockedError(LLMError):
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    code = "LLM_CONTENT_BLOCKED"
    message = "The request or response was blocked by the AI content policy."


class LLMEmptyResponseError(LLMError):
    code = "LLM_EMPTY_RESPONSE"
    message = "The AI service returned an empty response. Please try again."


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def _error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    details: Any = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    body: dict[str, Any] = {
        "code": code,
        "message": message,
        "request_id": _request_id(request),
    }
    if details is not None:
        body["details"] = details
    return JSONResponse(status_code=status_code, content={"error": body}, headers=headers)


async def _handle_app_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)
    log = logger.error if exc.status_code >= 500 else logger.info
    log("Request failed: %s (%s)", exc.code, exc.status_code)
    return _error_response(
        request,
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        headers=exc.headers,
    )


async def _handle_validation_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    details = [
        {"field": ".".join(str(part) for part in err["loc"][1:]), "message": err["msg"]}
        for err in exc.errors()
    ]
    return _error_response(
        request,
        status_code=status.HTTP_400_BAD_REQUEST,
        code="INVALID_REQUEST",
        message="The request payload is invalid.",
        details=details,
    )


async def _handle_http_exception(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    return _error_response(
        request,
        status_code=exc.status_code,
        code="HTTP_ERROR",
        message=str(exc.detail),
        headers=exc.headers,
    )


async def _handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error", exc_info=exc)
    return _error_response(
        request,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code=AppError.code,
        message=AppError.message,
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _handle_app_error)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, _handle_http_exception)
    app.add_exception_handler(Exception, _handle_unexpected_error)
