"""Module containing the model for adjacent samples."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class AdjancentResultView(BaseModel):
    """Result of getting adjacent samples."""

    sample_previous_id: UUID | None
    sample_id: UUID
    sample_next_id: UUID | None
    position: int | None
