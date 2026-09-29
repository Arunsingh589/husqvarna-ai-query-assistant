from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import Settings
from app.core.errors import AuthenticationError, RateLimitExceededError
from app.core.rate_limit import SlidingWindowRateLimiter
from app.core.security import decode_access_token
from app.llm import LLMProvider

_bearer_scheme = HTTPBearer(auto_error=False)


def get_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def get_llm_provider(request: Request) -> LLMProvider:
    provider: LLMProvider = request.app.state.llm_provider
    return provider


SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_current_subject(
    settings: SettingsDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
) -> str:
    if credentials is None:
        raise AuthenticationError()
    claims = decode_access_token(credentials.credentials, settings)
    return str(claims["sub"])


CurrentSubject = Annotated[str, Depends(get_current_subject)]


def enforce_rate_limit(request: Request, subject: CurrentSubject) -> None:
    limiter: SlidingWindowRateLimiter = request.app.state.rate_limiter
    retry_after = limiter.check(subject)
    if retry_after is not None:
        raise RateLimitExceededError(retry_after)


LLMProviderDep = Annotated[LLMProvider, Depends(get_llm_provider)]
