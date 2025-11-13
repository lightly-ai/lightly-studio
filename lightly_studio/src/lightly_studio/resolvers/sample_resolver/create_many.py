"""Implementation of create_many for sample resolver."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import ScalarResult
from sqlmodel import Session, col, insert

from lightly_studio.models.sample import SampleCreate, SampleTable


def create_many(session: Session, samples: Sequence[SampleCreate]) -> list[UUID]:
    """Create multiple samples in a single database commit."""
    if not samples:
        return []
    # Note: We are using bulk insert for SampleTable to get sample_ids efficiently.
    statement = (
        insert(SampleTable)
        .values([sample.model_dump() for sample in samples])
        .returning(col(SampleTable.sample_id))
    )
    sample_ids: ScalarResult[UUID] = session.execute(statement).scalars()
    return list(sample_ids)
