"""Implementation of create_many for sample resolver."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID, uuid4

from sqlmodel import Session, insert

from lightly_studio.models.sample import SampleCreate, SampleTable
from lightly_studio.utils import batching


def create_many(session: Session, samples: Sequence[SampleCreate]) -> list[UUID]:
    """Create multiple samples in a single database commit."""
    if not samples:
        return []
    # Generate sample_ids client-side so the returned order does not depend on
    # INSERT ... RETURNING preserving VALUES order (not guaranteed by PostgreSQL).
    sample_ids = [uuid4() for _ in samples]
    rows = [
        {**sample.model_dump(), "sample_id": sample_id}
        for sample, sample_id in zip(samples, sample_ids)
    ]
    for batch in batching.batched(items=rows):
        session.execute(insert(SampleTable).values(batch))
    return sample_ids
