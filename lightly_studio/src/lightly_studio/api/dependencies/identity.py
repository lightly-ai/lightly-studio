"""The user and the role that send a request."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Annotated

from fastapi import Depends, Request

from lightly_studio import deployment
from lightly_studio.database.db_manager import SessionDep
from lightly_studio.errors import UnauthenticatedError

_EMAIL_HEADER = "X-User-Email"
_ROLE_HEADER = "X-User-Role"


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


def get_identity(session: SessionDep, request: Request) -> Identity:
    """Returns the user's identity from the headers sent in enterprise deployments.

    A local run has no user identity. Every request is an anonymous admin.

    Raises:
        RuntimeError: If a local run gets the headers.
        UnauthenticatedError: If an enterprise server gets a request without an email, with
            an unknown role, or with a header sent more than once.
    """
    emails = request.headers.getlist(_EMAIL_HEADER)
    roles = request.headers.getlist(_ROLE_HEADER)
    if not deployment.is_enterprise(session=session):
        if emails or roles:
            raise RuntimeError("Authentication is not supported in a local run.")
        return Identity(email=None, role=Role.ADMIN)

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


def _single_header(name: str, values: list[str]) -> str:
    """Returns the one value of a header, or an empty string if the header is missing."""
    if len(values) > 1:
        raise UnauthenticatedError(f"The {name} header is sent more than once.")
    return values[0] if values else ""
