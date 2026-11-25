"""Test doubles for the API dependencies."""

from __future__ import annotations

from typing_extensions import override

from lightly_studio.api.dependencies.authorization import Action, Policy
from lightly_studio.api.dependencies.identity import Identity


def get_deny_all_policy() -> Policy:
    """Returns a policy that denies every action. Use it to replace `get_policy`."""
    return _DenyAll()


class _DenyAll(Policy):
    @override
    def allows(self, identity: Identity, action: Action) -> bool:
        return False
