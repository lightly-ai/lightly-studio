"""The user and the role that send a request."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request
from sqlmodel import Session

from lightly_studio import deployment
from lightly_studio.database.db_manager import SessionDep
from lightly_studio.errors import ForbiddenError, UnauthenticatedError
from lightly_studio.models.user import Role, UserStatus
from lightly_studio.resolvers import user_resolver

_EMAIL_HEADER = "X-User-Email"
_ROLE_HEADER = "X-User-Role"

_ROLE_RANK: dict[Role, int] = {
    Role.VIEWER: 0,
    Role.LABELER: 1,
    Role.EDITOR: 2,
    Role.ADMIN: 3,
}


@dataclass(frozen=True)
class Identity:
    """The user that sends a request.

    Attributes:
        email: The email of the user. None for a local run without an auth proxy.
        role: The role of the user.
        user_id: The ID of the user in `auth.users`. None for a local run without an auth proxy.
    """

    email: str | None
    role: Role
    user_id: int | None


def get_identity(session: SessionDep, request: Request) -> Identity:
    """Returns the identity of the user that sends a request.

    A local run has no user identity. Every request is an anonymous admin.

    Raises:
        RuntimeError: If a local run gets the headers.
        UnauthenticatedError: If an enterprise server gets a request that has no active user.
            See `_get_enterprise_identity`.
    """
    emails = request.headers.getlist(_EMAIL_HEADER)
    roles = request.headers.getlist(_ROLE_HEADER)
    if not deployment.is_enterprise(session=session):
        if emails or roles:
            raise RuntimeError("Authentication is not supported in a local run.")
        return Identity(email=None, role=Role.ADMIN, user_id=None)
    return _get_enterprise_identity(session=session, emails=emails, roles=roles)


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


def _get_enterprise_identity(session: Session, emails: list[str], roles: list[str]) -> Identity:
    """Returns the identity of the user that the auth proxy verified.

    The role and the status come from `auth.users`, because the proxy caches its headers.
    The role header shows that the proxy verified the request, but its value is not used.

    Raises:
        UnauthenticatedError: If the email or the role header is missing or empty, if a header
            is sent more than once, or if no active user has the email.
    """
    email = _single_header(name=_EMAIL_HEADER, values=emails).strip().lower()
    if not email:
        raise UnauthenticatedError(f"The {_EMAIL_HEADER} header is missing or empty.")
    if not _single_header(name=_ROLE_HEADER, values=roles).strip():
        raise UnauthenticatedError(f"The {_ROLE_HEADER} header is missing or empty.")

    user = user_resolver.get_by_email(session=session, email=email)
    if user is None:
        raise UnauthenticatedError(f"No user has the email '{email}'.")
    if user.status != UserStatus.ACTIVE:
        raise UnauthenticatedError(f"The user '{email}' is not active: '{user.status}'.")
    return Identity(email=email, role=Role(user.role), user_id=user.id)


def _single_header(name: str, values: list[str]) -> str:
    """Returns the one value of a header, or an empty string if the header is missing."""
    if len(values) > 1:
        raise UnauthenticatedError(f"The {name} header is sent more than once.")
    return values[0] if values else ""
