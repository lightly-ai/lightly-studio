"""Module containing the model for adjacent samples."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class AdjacentResultView(BaseModel):
    """Result of getting adjacent samples."""

    previous_sample_id: UUID | None
    sample_id: UUID
    next_sample_id: UUID | None
    current_sample_position: int
    total_count: int
