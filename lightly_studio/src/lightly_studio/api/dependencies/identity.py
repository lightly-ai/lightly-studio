"""The user and the role that send a request.

`get_identity` is a hook. The default returns the local user. A deployment with an auth proxy
overrides it: `app.dependency_overrides[identity.get_identity] = identity.get_proxy_identity`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Annotated

from fastapi import Depends, Request

from lightly_studio.errors import ForbiddenError, UnauthenticatedError

_EMAIL_HEADER = "X-User-Email"
_ROLE_HEADER = "X-User-Role"


class Role(str, Enum):
    """The role of a user. Each role includes the permissions of the roles before it."""

    VIEWER = "viewer"
    LABELER = "labeler"
    EDITOR = "editor"
    ADMIN = "admin"


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
        email: The email of the user. None for the local user.
        role: The role of the user.
    """

    email: str | None
    role: Role


LOCAL_USER = Identity(email=None, role=Role.ADMIN)


def get_identity(request: Request) -> Identity:
    """Returns the local user. Every request is the same anonymous admin.

    Raises:
        RuntimeError: If the request carries user headers. They are only valid behind an auth
            proxy, and that deployment overrides this dependency with `get_proxy_identity`.
    """
    if request.headers.getlist(_EMAIL_HEADER) or request.headers.getlist(_ROLE_HEADER):
        raise RuntimeError("User headers are not supported in a local run.")
    return LOCAL_USER


def get_proxy_identity(request: Request) -> Identity:
    """Returns the user's identity from the headers that an auth proxy sets.

    Raises:
        UnauthenticatedError: If the request has no email, an unknown role, or a header sent
            more than once.
    """
    emails = request.headers.getlist(_EMAIL_HEADER)
    roles = request.headers.getlist(_ROLE_HEADER)
    email = _single_header(name=_EMAIL_HEADER, values=emails).strip().lower()
    if not email:
        raise UnauthenticatedError(f"The {_EMAIL_HEADER} header is missing or empty.")
    role_value = _single_header(name=_ROLE_HEADER, values=roles).strip().lower()
    try:
        role = Role(role_value)
    except ValueError as error:
        raise UnauthenticatedError(
            f"The {_ROLE_HEADER} header has an unknown role: '{role_value}'."
        ) from error
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


def _single_header(name: str, values: list[str]) -> str:
    """Returns the one value of a header, or an empty string if the header is missing."""
    if len(values) > 1:
        raise UnauthenticatedError(f"The {name} header is sent more than once.")
    return values[0] if values else ""
