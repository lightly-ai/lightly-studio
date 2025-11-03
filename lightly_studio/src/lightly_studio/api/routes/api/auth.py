"""This module contains the API routes for authentication."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing_extensions import Annotated

from lightly_studio.auth.dependencies import CurrentUser
from lightly_studio.auth.utils import create_access_token, verify_password
from lightly_studio.db_manager import SessionDep
from lightly_studio.models.user import UserView
from lightly_studio.resolvers import user_resolver

auth_router = APIRouter()


class Token(BaseModel):
    """Token response model."""

    access_token: str
    token_type: str
    user: UserView


@auth_router.post("/auth/login", response_model=Token)
def login(
    session: SessionDep,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Token:
    """Authenticate a user and return a JWT token.

    Args:
        session: The database session.
        form_data: OAuth2 form data containing username (email) and password.

    Returns:
        A token response with access_token and user info.

    Raises:
        HTTPException: If credentials are invalid.
    """
    # Get user by email (OAuth2 spec uses 'username' field for email)
    user = user_resolver.get_by_email(session=session, email=form_data.username)

    # Verify user exists and password is correct
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token
    access_token = create_access_token(data={"sub": str(user.user_id)})

    # Return token with user info
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserView(
            user_id=user.user_id,
            email=user.email,
            created_at=user.created_at,
            updated_at=user.updated_at,
        ),
    )


@auth_router.get("/auth/me", response_model=UserView)
def get_current_user_info(
    current_user: CurrentUser,
) -> UserView:
    """Get the current authenticated user's information.

    Args:
        current_user: The authenticated user from the JWT token.

    Returns:
        The user's information (without password).
    """
    return UserView(
        user_id=current_user.user_id,
        email=current_user.email,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
    )
