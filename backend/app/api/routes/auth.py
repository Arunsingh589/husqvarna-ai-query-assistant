from typing import Annotated

from fastapi import APIRouter, Body

from app.api.dependencies import SettingsDep
from app.core.security import create_access_token
from app.schemas import TokenRequest, TokenResponse

router = APIRouter(prefix="/api/auth", tags=["auth (dev only)"])


@router.post("/token", response_model=TokenResponse)
async def issue_dev_token(
    settings: SettingsDep,
    payload: Annotated[TokenRequest | None, Body()] = None,
) -> TokenResponse:
    subject = (payload or TokenRequest()).subject
    token, expires_in = create_access_token(subject, settings)
    return TokenResponse(access_token=token, expires_in=expires_in)
