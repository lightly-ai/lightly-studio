"""JWT token decoding module."""

from typing import Any

from jose import JWTError, jwt

from lightly_studio.auth import jwt_config
from lightly_studio.auth.jwt_config import JWTPayload


def decode_token(token: str) -> JWTPayload | None:
    """Decodes and validates a JWT token.

    Args:
        token: The JWT token string to decode.

    Returns:
        The decoded JWT payload if valid, None if invalid or expired.

    Raises:
        ValueError: If JWT_SECRET is not configured.
    """
    if jwt_config.JWT_SECRET is None:
        raise ValueError("JWT_SECRET must be configured")
    try:
        payload: dict[str, Any] = jwt.decode(
            token, jwt_config.JWT_SECRET, algorithms=[jwt_config.JWT_ALGORITHM]
        )
        return payload  # type: ignore[return-value]
    except JWTError:
        return None
