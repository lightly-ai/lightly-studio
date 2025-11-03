"""Implementation of create functions for images."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.image import ImageCreate, ImageTable
from lightly_studio.models.sample import SampleCreate
from lightly_studio.resolvers import sample_resolver


class ImageCreateHelper(ImageCreate):
    """Helper class to create ImageTable with sample_id."""

    sample_id: UUID


def create(session: Session, sample: ImageCreate) -> ImageTable:
    """Create a new sample in the database."""
    # Check that the dataset has a correct sample type.
    # dataset = dataset_resolver.get_by_id(session=session, dataset_id=sample.dataset_id)
    # assert dataset is not None, f"Dataset with id {sample.dataset_id} not found."
    # if dataset.sample_type != SampleType.IMAGE:
    #     raise ValueError(
    #         f"Dataset with id {sample.dataset_id} is having sample type "
    #         f"{dataset.sample_type}, cannot add image sample."
    #     )

    # TODO(Michal, 10/2025): Temporarily create sample table entry here until
    # ImageTable and SampleTable are properly split.
    db_sample = sample_resolver.create(
        session=session,
        sample=SampleCreate(dataset_id=sample.dataset_id),
    )
    # Use the helper class to provide sample_id.
    db_image = ImageTable.model_validate(
        ImageCreateHelper(
            file_name=sample.file_name,
            width=sample.width,
            height=sample.height,
            dataset_id=sample.dataset_id,
            file_path_abs=sample.file_path_abs,
            sample_id=db_sample.sample_id,
        )
    )
    session.add(db_image)
    session.commit()
    session.refresh(db_image)
    return db_image


def create_many(session: Session, samples: list[ImageCreate]) -> list[ImageTable]:
    """Create multiple samples in a single database commit."""
    # TODO(Michal, 10/2025): Temporarily create sample table entry here until
    # ImageTable and SampleTable are properly split.
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
    return db_images
