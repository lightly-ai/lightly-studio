"""Implementation of delete dataset resolver function."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.resolvers import collection_resolver


def delete(session: Session, dataset_id: UUID) -> bool:
    """Delete a dataset."""
    dataset = collection_resolver.get_by_id(session=session, dataset_id=dataset_id)
    if not dataset:
        return False

    session.delete(dataset)
    session.commit()
    return True
