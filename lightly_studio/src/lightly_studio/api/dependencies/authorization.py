"""The actions a user may do.

`get_policy` is a hook. The default allows every action for the local user. A deployment with
several users overrides it with `app.dependency_overrides`.
"""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum
from typing import Annotated, Protocol

from fastapi import Depends

from lightly_studio.api.dependencies.identity import Identity, IdentityDep
from lightly_studio.errors import ForbiddenError


class Action(str, Enum):
    """An action a user can do. The value is the name the API returns."""

    DATASET_DELETE = "dataset.delete"


class Policy(Protocol):
    """Decides which actions a user may do."""

    def allows(self, identity: Identity, action: Action) -> bool:
        """Returns True if `identity` may do `action`."""


class AllowAll:
    """The policy for one local user: every action is allowed."""

    def allows(self, identity: Identity, action: Action) -> bool:  # noqa: ARG002
        """Returns True for every identity and action."""
        return True


def get_policy() -> Policy:
    """Returns the policy of this deployment."""
    return AllowAll()


PolicyDep = Annotated[Policy, Depends(get_policy)]


def require(action: Action) -> Callable[[Identity, Policy], None]:
    """Returns a dependency that rejects a user who may not do `action`.

    Usage: `@router.delete(..., dependencies=[Depends(require(Action.DATASET_DELETE))])`.
    """

    def _check_action(identity: IdentityDep, policy: PolicyDep) -> None:
        if not policy.allows(identity=identity, action=action):
            raise ForbiddenError(f"The action '{action.value}' is not allowed.")

    return _check_action
