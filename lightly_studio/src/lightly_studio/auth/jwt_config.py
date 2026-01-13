"""JWT configuration module.

Loads JWT configuration from environment variables.
"""

from datetime import datetime
from typing import TypedDict

from environs import Env


class JWTPayload(TypedDict, total=False):
    """JWT token payload structure.

    Attributes:
        sub: Subject (typically user ID or username).
        email: User email.
        role: User role.
        exp: Expiration time.
    """

    sub: str
    email: str
    role: str
    exp: datetime


env = Env()
env.read_env()

JWT_SECRET: str | None = env.str("JWT_SECRET", None)
JWT_ALGORITHM: str = env.str("JWT_ALGORITHM", "HS256")
JWT_EXPIRATION_HOURS: int = env.int("JWT_EXPIRATION_HOURS", 24)
