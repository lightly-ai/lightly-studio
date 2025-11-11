"""Implementation of create for sample resolver."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.sample import SampleCreate, SampleTable


def create(session: Session, sample: SampleCreate) -> SampleTable:
    """Create a new sample in the database."""
    db_sample = SampleTable.model_validate(sample)
    session.add(db_sample)
    session.commit()
    session.refresh(db_sample)
    return db_sample
