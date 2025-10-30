"""FastAPI dependencies for authentication."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session

from lightly_studio import db_manager
from lightly_studio.auth.utils import decode_access_token
from lightly_studio.models.user import UserTable
from lightly_studio.resolvers import user_resolver

# OAuth2 scheme for extracting Bearer tokens from Authorization header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

SessionDep = Annotated[Session, Depends(db_manager.session)]


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: SessionDep,
) -> UserTable:
    """Get the current authenticated user from the JWT token.

    Args:
        token: The JWT token from the Authorization header.
        session: The database session.

    Returns:
        The authenticated user.

    Raises:
        HTTPException: If the token is invalid or the user doesn't exist.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Decode the token
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    # Extract user_id from token
    user_id_str: str | None = payload.get("sub")
    if user_id_str is None:
        raise credentials_exception

    try:
        user_id = UUID(user_id_str)
    except ValueError:
        raise credentials_exception

    # Get user from database
    user = user_resolver.get_by_id(session=session, user_id=user_id)
    if user is None:
        raise credentials_exception

    return user


# Type alias for dependency injection
CurrentUser = Annotated[UserTable, Depends(get_current_user)]