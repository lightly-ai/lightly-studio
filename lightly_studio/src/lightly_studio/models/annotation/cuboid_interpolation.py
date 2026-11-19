"""Models for cuboid interpolation along object tracks."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class CuboidInterpolationRange(BaseModel):
    """Inclusive tick range of one sequence and annotation source to interpolate."""

    sequence_id: UUID
    annotation_source_id: UUID
    start_seq_number: int
    end_seq_number: int
