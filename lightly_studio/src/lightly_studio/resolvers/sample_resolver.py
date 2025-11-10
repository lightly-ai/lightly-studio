"""Handler for database operations related to samples."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import ScalarResult
from sqlmodel import Session, col, func, insert, select

from lightly_studio.models.sample import SampleCreate, SampleTable


def create(session: Session, sample: SampleCreate) -> SampleTable:
    """Create a new sample in the database."""
    db_sample = SampleTable.model_validate(sample)
    session.add(db_sample)
    session.commit()
    session.refresh(db_sample)
    return db_sample


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


def get_by_id(session: Session, sample_id: UUID) -> SampleTable | None:
    """Retrieve a single sample by ID."""
    return session.exec(select(SampleTable).where(SampleTable.sample_id == sample_id)).one_or_none()


def get_many_by_id(session: Session, sample_ids: list[UUID]) -> list[SampleTable]:
    """Retrieve multiple samples by their IDs.

    Output order matches the input order.
    """
    results = session.exec(
        select(SampleTable).where(col(SampleTable.sample_id).in_(sample_ids))
    ).all()
    # Return samples in the same order as the input IDs
    sample_map = {sample.sample_id: sample for sample in results}
    return [sample_map[id_] for id_ in sample_ids if id_ in sample_map]


def count_by_dataset_id(session: Session, dataset_id: UUID) -> int:
    """Count the number of samples in a dataset."""
    return session.exec(
        select(func.count()).select_from(SampleTable).where(SampleTable.dataset_id == dataset_id)
    ).one()
