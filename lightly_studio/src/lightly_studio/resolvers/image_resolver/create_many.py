"""Implementation of create functions for images."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.models.image import ImageCreate, ImageTable
from lightly_studio.models.sample import SampleCreate
from lightly_studio.resolvers import collection_resolver, sample_resolver


class ImageCreateHelper(ImageCreate):
    """Helper class to create ImageTable with sample_id."""

    sample_id: UUID
    collection_id: UUID


def create_many(session: Session, collection_id: UUID, samples: list[ImageCreate]) -> list[UUID]:
    """Create multiple samples in a single database commit.

    Returns the list of created sample IDs that matches the order of input samples.
    """
    collection_resolver.check_collection_type(
        session=session,
        collection_id=collection_id,
        expected_type=SampleType.IMAGE,
    )
    sample_ids = sample_resolver.create_many(
        session=session,
        samples=[SampleCreate(collection_id=collection_id) for _ in samples],
    )
    # Bulk create ImageTable entries using the generated sample_ids.
    db_images = [
        ImageTable.model_validate(
            ImageCreateHelper(
                file_name=sample.file_name,
                width=sample.width,
                height=sample.height,
                collection_id=collection_id,
                file_path_abs=sample.file_path_abs,
                sample_id=sample_id,
            )
        )
        for sample_id, sample in zip(sample_ids, samples)
    ]
    session.bulk_save_objects(db_images)
    session.commit()
    return sample_ids
