"""Interface every analytics backend implements.

Lives apart from `tracking` so a backend can inherit it without importing the module that
builds it.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol


class Tracker(Protocol):
    """Delivers usage events to an analytics backend."""

    def identify(self, email: str) -> None:
        """Link the current anonymous ID to a known user email."""
        ...

    def track(self, event: str, properties: Mapping[str, object]) -> None:
        """Report a single event."""
        ...

    def shutdown(self) -> None:
        """Deliver anything still pending and release resources."""
        ...
