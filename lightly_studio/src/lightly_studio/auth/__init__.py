"""Authentication module for JWT-based authorization.

This module provides JWT token validation and role-based access control
for protecting API endpoints.
"""

from lightly_studio.auth.create_access_token import create_access_token
from lightly_studio.auth.decode_token import decode_token
from lightly_studio.auth.jwt_config import (
    JWT_ALGORITHM,
    JWT_EXPIRATION_HOURS,
    JWT_SECRET,
    JWTPayload,
)
from lightly_studio.auth.require_roles import require_roles

__all__ = [
    "JWT_ALGORITHM",
    "JWT_EXPIRATION_HOURS",
    "JWT_SECRET",
    "JWTPayload",
    "create_access_token",
    "decode_token",
    "require_roles",
]
