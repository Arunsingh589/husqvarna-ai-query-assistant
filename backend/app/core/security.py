from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import Settings
from app.core.errors import AuthenticationError

# never take the algorithm from the token itself
JWT_ALGORITHM = "HS256"


def create_access_token(subject: str, settings: Settings) -> tuple[str, int]:
    now = datetime.now(timezone.utc)
    expires_in = settings.jwt_expire_minutes * 60
    claims = {
        "sub": subject,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": now,
        "nbf": now,
        "exp": now + timedelta(seconds=expires_in),
    }
    token = jwt.encode(claims, settings.jwt_secret.get_secret_value(), algorithm=JWT_ALGORITHM)
    return token, expires_in


def decode_access_token(token: str, settings: Settings) -> dict[str, object]:
    try:
        return jwt.decode(
            token,
            settings.jwt_secret.get_secret_value(),
            algorithms=[JWT_ALGORITHM],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            options={"require": ["sub", "exp", "iat", "iss", "aud"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise AuthenticationError("Authentication token has expired.") from exc
    except jwt.InvalidTokenError as exc:
        raise AuthenticationError() from exc
