"""Implementation of create functions for images."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.dataset import SampleType
from lightly_studio.models.image import ImageCreate, ImageTable
from lightly_studio.models.sample import SampleCreate
from lightly_studio.resolvers import dataset_resolver, sample_resolver


class ImageCreateHelper(ImageCreate):
    """Helper class to create ImageTable with sample_id."""

    sample_id: UUID


def create_many(session: Session, samples: list[ImageCreate]) -> list[UUID]:
    """Create multiple samples in a single database commit."""
    dataset_ids = {sample.dataset_id for sample in samples}
    for dataset_id in dataset_ids:
        dataset_resolver.check_dataset_type(
            session=session,
            dataset_id=dataset_id,
            expected_type=SampleType.IMAGE,
        )

    sample_ids = sample_resolver.create_many(
        session=session,
        samples=[SampleCreate(dataset_id=sample.dataset_id) for sample in samples],
    )
    # Bulk create ImageTable entries using the generated sample_ids.
    db_images = [
        ImageTable.model_validate(
            ImageCreateHelper(
                file_name=sample.file_name,
                width=sample.width,
                height=sample.height,
                dataset_id=sample.dataset_id,
                file_path_abs=sample.file_path_abs,
                sample_id=sample_id,
            )
        )
        for sample_id, sample in zip(sample_ids, samples)
    ]
    session.bulk_save_objects(db_images)
    session.commit()
    return sample_ids
