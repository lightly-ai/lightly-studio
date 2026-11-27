"""The dependencies that a caller of `create_app` may replace."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from lightly_studio.api.dependencies import authorization, identity
from lightly_studio.api.dependencies.authorization import Policy
from lightly_studio.api.dependencies.identity import Identity


@dataclass(frozen=True)
class Replaceable:
    """Each dependency that a caller of `create_app` may replace, with its default.

    A field is one dependency. Its default is the function that routes use in
    `Depends(...)`. A deployment passes a replacement for each dependency that it changes:
    `create_app(replace=Replaceable(get_identity=...))`. FastAPI then calls the replacement
    instead of the default, and resolves the `Depends(...)` parameters of the replacement.

    Attributes:
        get_identity: Returns the user that sends a request. The default returns the local
            user. A deployment behind an auth proxy uses `identity.get_proxy_identity`.
        get_policy: Returns the policy that decides which actions a user may do. The default
            allows every action.
    """

    get_identity: Callable[..., Identity] = identity.get_identity
    get_policy: Callable[..., Policy] = authorization.get_policy


# The functions of `api.dependencies` that routes may use and that are not replaceable. A
# function that creates a new dependency for each route stands for each dependency it creates.
# A test checks that each such function in a route is a field of `Replaceable` or in this list.
NOT_REPLACEABLE: tuple[Callable[..., object], ...] = (
    # Creates the check of one action. The check uses `get_identity` and `get_policy`, which
    # are replaceable.
    authorization.require,
)
