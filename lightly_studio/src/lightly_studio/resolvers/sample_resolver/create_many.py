"""Implementation of create_many for sample resolver."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import ScalarResult
from sqlmodel import Session, col, insert

from lightly_studio.models.sample import SampleCreate, SampleTable
from lightly_studio.utils import batching


def create_many(session: Session, samples: Sequence[SampleCreate]) -> list[UUID]:
    """Create multiple samples in a single database commit."""
    if not samples:
        return []
    # Bulk insert in batches so the bind-parameter count of any single statement
    # stays under PostgreSQL's 65,535 limit. RETURNING yields ids in VALUES order
    # and batches are iterated in order, so the result matches the input order
    # that downstream callers rely on (do not collect into a set).
    sample_ids: list[UUID] = []
    for batch in batching.batched(samples, batching.INSERT_BATCH_SIZE):
        statement = (
            insert(SampleTable)
            .values([sample.model_dump() for sample in batch])
            .returning(col(SampleTable.sample_id))
        )
        result: ScalarResult[UUID] = session.execute(statement).scalars()
        sample_ids.extend(result)
    return sample_ids
