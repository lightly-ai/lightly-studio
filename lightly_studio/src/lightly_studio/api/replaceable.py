"""The dependencies that a caller of `create_app` may replace."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from lightly_studio.api.dependencies import identity
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
    """

    get_identity: Callable[..., Identity] = identity.get_identity
