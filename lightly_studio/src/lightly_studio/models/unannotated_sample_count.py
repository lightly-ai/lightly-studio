"""Count of the samples without annotations."""

from __future__ import annotations

from pydantic import BaseModel


class UnannotatedSampleCount(BaseModel):
    """Number of samples without annotations in the selected annotation sources.

    Attributes:
        current_count: Unannotated samples that match the filter.
        total_count: Unannotated samples in the collection.
    """

    current_count: int
    total_count: int
