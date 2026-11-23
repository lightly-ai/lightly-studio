"""Service function that checks whether an MCAP sequence belongs to a dataset."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.resolvers import (
    collection_resolver,
    mcap_group_sequence_resolver,
    sample_resolver,
)


def sequence_belongs_to_dataset(session: Session, sequence_id: UUID, dataset_id: UUID) -> bool:
    """Whether `sequence_id` is an MCAP sequence whose collection is in `dataset_id`.

    Membership derives from the sequence sample's own collection, not from its
    recording: the two can differ, and a sequence has a valid collection even before
    its GROUP component schema exists.
    """
    if mcap_group_sequence_resolver.get_by_id(session=session, sample_id=sequence_id) is None:
        return False
    sample = sample_resolver.get_by_id(session=session, sample_id=sequence_id)
    if sample is None:
        return False
    collection = collection_resolver.get_by_id(session=session, collection_id=sample.collection_id)
    return collection is not None and collection.dataset_id == dataset_id
