"""Handler for database operations related to samples."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy.orm import joinedload, selectinload
from sqlmodel import Session, col, func, select
from sqlmodel.sql.expression import Select

from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.embedding_model import EmbeddingModelTable
from lightly_studio.models.image import ImageCreate, ImageTable
from lightly_studio.models.dataset import DatasetTable
from lightly_studio.models.sample import SampleCreate, SampleTable
from lightly_studio.models.sample_embedding import SampleEmbeddingTable
from lightly_studio.models.tag import TagTable
from lightly_studio.models.sample_type import SampleType
from lightly_studio.resolvers import sample_resolver
from lightly_studio.resolvers.samples_filter import SampleFilter


class ImageCreateHelper(ImageCreate):
    """Helper class to create ImageTable with sample_id."""

    sample_id: UUID


def create(session: Session, sample: ImageCreate) -> ImageTable:
    """Create a new sample in the database."""
    # Check that the dataset has a correct sample type.
    # Note: Avoid a circular import by querying DatasetTable directly.
    dataset = session.exec(
        select(DatasetTable).where(
            DatasetTable.dataset_id == sample.dataset_id
        )
    ).one_or_none()
    assert dataset is not None, "Dataset does not exist."
    if dataset.sample_type != SampleType.IMAGE:
        raise ValueError(
            f"Dataset {dataset.name} has sample type {dataset.sample_type}, "
            f"cannot add image sample."
        )

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
