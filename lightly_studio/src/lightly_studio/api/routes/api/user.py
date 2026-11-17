"""API routes for the users of an enterprise deployment."""

from __future__ import annotations

from fastapi import APIRouter

from lightly_studio.api.dependencies.identity import IdentityDep
from lightly_studio.database.db_manager import SessionDep
from lightly_studio.errors import NotFoundError
from lightly_studio.models.user import UserView
from lightly_studio.resolvers import user_resolver

user_router = APIRouter(tags=["users"])


@user_router.get("/me")
def get_me(session: SessionDep, identity: IdentityDep) -> UserView | None:
    """Returns the user that sends the request.

    Returns None for a local run, because a local run has no users.
    """
    if identity.user_id is None:
        return None
    user = user_resolver.get_by_id(session=session, user_id=identity.user_id)
    if user is None:
        raise NotFoundError(f"User {identity.user_id} does not exist.")
    return UserView.model_validate(user)
