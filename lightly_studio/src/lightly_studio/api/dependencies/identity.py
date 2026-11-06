"""The user and the role that send a request."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Annotated

from fastapi import Depends, Header

from lightly_studio import deployment
from lightly_studio.errors import UnauthenticatedError


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
    x_user_email: Annotated[str | None, Header()] = None,
    x_user_role: Annotated[str | None, Header()] = None,
) -> Identity:
    """Returns the identity from the headers of the auth proxy.

    An enterprise server runs behind the auth proxy, which overwrites both headers on every
    request. A local run has no auth proxy, and every request is an anonymous admin.

    Raises:
        RuntimeError: If a local run gets the headers. An auth proxy sends them, so the server
            is an enterprise server without the enterprise mode. This fails closed.
        UnauthenticatedError: If an enterprise server gets a request without an email or with
            an unknown role.
    """
    if not deployment.is_enterprise():
        if x_user_email is not None or x_user_role is not None:
            raise RuntimeError(
                "Authentication is not supported in a local run. For an enterprise server, set "
                "LIGHTLY_STUDIO_DEPLOYMENT_MODE=enterprise."
            )
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
