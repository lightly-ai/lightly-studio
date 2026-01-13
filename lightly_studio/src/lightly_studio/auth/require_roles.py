"""Role-based access control dependency for FastAPI endpoints.

This module provides a stateless JWT-based role validation dependency
that trusts the role claim in the JWT token without database lookup.
"""

from collections.abc import Callable, Sequence

from fastapi import Depends, status
from fastapi.exceptions import HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from lightly_studio.auth.decode_token import decode_token
from lightly_studio.auth.jwt_config import JWTPayload

security = HTTPBearer(auto_error=False)


class Role(Enum):
    ADMIN = "admin"
    MODERATOR = "moderator"
    VIEWER = "viewer"


def require_roles(allowed_roles: Sequence[Role]) -> Callable[..., JWTPayload]:
    """Factory function that creates a dependency to check user roles.

    Args:
        allowed_roles: Collection of allowed roles (e.g., [Role.ADMIN]).

    Returns:
        A dependency function that validates the user's role.

    Raises:
        HTTPException: 401 if token is invalid, 403 if user lacks permissions.
    """
    allowed_role_values = {role.value for role in allowed_roles}

    def role_checker(
        credentials: HTTPAuthorizationCredentials | None = Depends(security),
    ) -> JWTPayload:
        """Validates user token and checks if user has required role.

        Args:
            credentials: Bearer token credentials.
            db: Database session dependency.

        Returns:
            JWT payload dictionary.

        Raises:
            HTTPException: 401 if token is invalid, 403 if user lacks permissions.
        """
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing authentication token",
            )

        payload = decode_token(credentials.credentials)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )

        # Get username from token payload
        username = payload.get("sub")
        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )

        # Get role from token payload and check permissions
        role = payload.get("role", "").lower()
        if role not in allowed_role_values:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )

        return payload

    return role_checker
