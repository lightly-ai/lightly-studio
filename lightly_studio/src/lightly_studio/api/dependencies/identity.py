"""The user and the role that send a request."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Annotated

from fastapi import Depends, Header

from lightly_studio import deployment
from lightly_studio.database.db_manager import SessionDep
from lightly_studio.errors import ForbiddenError, UnauthenticatedError


class Role(str, Enum):
    """The role of a user. Each role includes the permissions of the roles before it."""

    VIEWER = "viewer"
    LABELER = "labeler"
    EDITOR = "editor"
    ADMIN = "admin"


@dataclass(frozen=True)
class Identity:
    """The user that sends a request.

    Attributes:
        email: The email of the user. None for a local run without an auth proxy.
        role: The role of the user.
    """

    email: str | None
    role: Role


def get_identity(
    session: SessionDep,
    x_user_email: Annotated[str | None, Header()] = None,
    x_user_role: Annotated[str | None, Header()] = None,
) -> Identity:
    """Returns the identity from the headers of the auth proxy.

    An enterprise server runs behind the auth proxy, which overwrites both headers on every
    request. A local run has no auth proxy, and every request is an anonymous admin.

    Raises:
        RuntimeError: If a local run gets the headers. An auth proxy sends them, so the server
            is an enterprise server on DuckDB. This fails closed.
        UnauthenticatedError: If an enterprise server gets a request without an email or with
            an unknown role.
    """
    if not deployment.is_enterprise(session=session):
        if x_user_email is not None or x_user_role is not None:
            raise RuntimeError("Authentication is not supported in a local run.")
        return Identity(email=None, role=Role.ADMIN)

    email = (x_user_email or "").strip()
    if not email:
        raise UnauthenticatedError("The request has no valid user identity.")
    try:
        role = Role((x_user_role or "").strip().lower())
    except ValueError as error:
        raise UnauthenticatedError("The request has no valid user identity.") from error
    return Identity(email=email, role=role)


IdentityDep = Annotated[Identity, Depends(get_identity)]


def require_role(min_role: Role) -> Callable[[Identity], Identity]:
    """Returns a dependency that rejects users with a role lower than `min_role`.

    Usage: `identity: Annotated[Identity, Depends(require_role(min_role=Role.EDITOR))]`.
    """

    def _check_role(identity: IdentityDep) -> Identity:
        if _ROLE_RANK[identity.role] < _ROLE_RANK[min_role]:
            raise ForbiddenError(f"Requires the {min_role.value} role or higher.")
        return identity

    return _check_role


_ROLE_RANK: dict[Role, int] = {
    Role.VIEWER: 0,
    Role.LABELER: 1,
    Role.EDITOR: 2,
    Role.ADMIN: 3,
}
