"""JWT token creation module."""

from datetime import UTC, datetime, timedelta

from jose import jwt

from lightly_studio.auth import jwt_config
from lightly_studio.auth.jwt_config import JWTPayload


def create_access_token(data: JWTPayload, expires_delta: timedelta | None = None) -> str:
    """Creates a JWT access token with the provided payload.

    Args:
        data: The JWT payload containing user information.
        expires_delta: Optional custom expiration time delta. If not provided,
            uses the default expiration from configuration.

    Returns:
        The encoded JWT token string.

    Raises:
        ValueError: If JWT_SECRET is not configured.
    """
    if jwt_config.JWT_SECRET is None:
        raise ValueError("JWT_SECRET must be configured")
    to_encode = dict(data)
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(hours=jwt_config.JWT_EXPIRATION_HOURS)
    to_encode.update({"exp": expire})
    encoded_jwt: str = jwt.encode(
        to_encode, jwt_config.JWT_SECRET, algorithm=jwt_config.JWT_ALGORITHM
    )
    return encoded_jwt
