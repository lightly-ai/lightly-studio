"""Transport protocol for samples."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from lightly_studio.models.sample import SampleView


# TODO(Iunir, 11/2026): Return a model without DB tables. `SampleView.tags` holds `TagTable`.
class SampleTransport(Protocol):
    """Gets samples."""

    def get_by_ids(self, sample_ids: Sequence[UUID]) -> list[SampleView]:
        """Get samples by ID. Samples that do not exist are not in the result."""
