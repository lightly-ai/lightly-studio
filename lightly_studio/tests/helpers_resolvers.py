"""Helper functions for tests."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Generator
from uuid import UUID

import pytest
from sqlmodel import Session, SQLModel, create_engine

from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
    AnnotationCreate,
    AnnotationType,
)
from lightly_studio.models.annotation_label import (
    AnnotationLabelCreate,
    AnnotationLabelTable,
)
from lightly_studio.models.dataset import DatasetCreate, DatasetTable
from lightly_studio.models.sample_type import SampleType
from lightly_studio.models.embedding_model import (
    EmbeddingModelCreate,
    EmbeddingModelTable,
)
from lightly_studio.models.image import ImageCreate, ImageTable
from lightly_studio.models.sample_embedding import (
    SampleEmbeddingCreate,
    SampleEmbeddingTable,
)
from lightly_studio.models.tag import TagCreate, TagKind, TagTable
from lightly_studio.resolvers import (
    annotation_label_resolver,
    annotation_resolver,
    dataset_resolver,
    embedding_model_resolver,
    image_resolver,
    sample_embedding_resolver,
    tag_resolver,
)
from lightly_studio.type_definitions import PathLike


@pytest.fixture
def test_db() -> Generator[Session, None, None]:
    """Fixture which yields an in-memory database unique to a test."""
    # Setup a test database
    engine = create_engine("duckdb:///:memory:")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        yield session


def create_dataset(session: Session, dataset_name: str = "example_tag", sample_type: SampleType = SampleType.IMAGE) -> DatasetTable:
    """Helper function to create a dataset."""
    return dataset_resolver.create(
        session=session,
        dataset=DatasetCreate(name=dataset_name, sample_type=sample_type),
    )


def create_tag(
    session: Session,
    dataset_id: UUID,
    tag_name: str = "example_tag",
    kind: TagKind = "sample",
) -> TagTable:
    """Helper function to create a tag."""
    return tag_resolver.create(
        session=session,
        tag=TagCreate(
            dataset_id=dataset_id,
            name=tag_name,
            kind=kind,
            description="example description",
        ),
    )


def create_image(
    session: Session,
    dataset_id: UUID,
    file_path_abs: str = "/path/to/sample1.png",
    width: int = 1920,
    height: int = 1080,
) -> ImageTable:
    """Helper function to create a sample."""
    return image_resolver.create(
        session=session,
        sample=ImageCreate(
            dataset_id=dataset_id,
            file_path_abs=file_path_abs,
            file_name=Path(file_path_abs).name,
            width=width,
            height=height,
        ),
    )


@dataclass
class SampleImage:
    """Helper class to represent a sample image for testing.

    Attributes:
        path: Location of the image file.
        width: Width of the image in pixels.
        height: Height of the image in pixels.
    """

    path: PathLike = "test_image.jpg"
    width: int = 640
    height: int = 480


def create_images(
    db_session: Session,
    dataset_id: UUID,
    images: list[SampleImage],
) -> list[ImageTable]:
    """Creates samples in the database for a given dataset.

    Args:
        db_session: The database session.
        dataset_id: The ID of the dataset to add samples to.
        images: A list of SampleImage objects representing the samples to create.

    Returns:
        A list of the created ImageTable objects.
    """
    return [
        create_image(
            session=db_session,
            dataset_id=dataset_id,
            file_path_abs=str(image.path),
            width=image.width,
            height=image.height,
        )
        for image in images
    ]


def create_annotation_label(
    session: Session,
    annotation_label_name: str = "cat",
) -> AnnotationLabelTable:
    """Helper function to insert an annotation label."""
    return annotation_label_resolver.create(
        session=session,
        label=AnnotationLabelCreate(annotation_label_name=annotation_label_name),
    )


def get_annotation_by_type(
    annotations: Sequence[AnnotationBaseTable],
    annotation_type: AnnotationType,
) -> AnnotationBaseTable:
    """Retrieve the first annotation matching the given type."""
    return next(
        annotation for annotation in annotations if annotation.annotation_type == annotation_type
    )


def create_annotation(
    session: Session,
    dataset_id: UUID,
    sample_id: UUID,
    annotation_label_id: UUID,
    annotation_data: dict[str, Any] | None = None,
) -> AnnotationBaseTable:
    """Helper function to create an annotation."""
    annotation_data_default = {
        "x": 50,
        "y": 50,
        "width": 20,
        "height": 20,
    }

    annotation_data = annotation_data or {}
    annotation_data = {**annotation_data_default, **annotation_data}

    annotation_ids = annotation_resolver.create_many(
        session=session,
        annotations=[
            AnnotationCreate(
                dataset_id=dataset_id,
                sample_id=sample_id,
                annotation_label_id=annotation_label_id,
                annotation_type="object_detection",
                **(annotation_data),
            )
        ],
    )
    assert len(annotation_ids) == 1
    annotation = annotation_resolver.get_by_id(session=session, annotation_id=annotation_ids[0])
    assert annotation is not None, "Failed to retrieve the created annotation."
    return annotation


@dataclass
class AnnotationDetails:
    """Helper class to represent a annotation for testing.

    Attributes:
        sample_id: ID of the sample.
        annotation_label_id: ID of the annotation label.
        annotation_type: Type of the annotation.
        confidence: Confidence score of the annotation.
        x: X coordinate of the annotation.
        y: Y coordinate of the annotation.
        width: Width of the annotation.
        height: Height of the annotation.
        segmentation_mask: Segmentation mask for instance and semantic segmentation annotations.
    """

    sample_id: UUID
    annotation_label_id: UUID
    annotation_type: AnnotationType = AnnotationType.OBJECT_DETECTION
    confidence: float | None = None
    x: int = 10
    y: int = 10
    width: int = 20
    height: int = 20
    segmentation_mask: list[int] | None = None


def create_annotations(
    session: Session, dataset_id: UUID, annotations: list[AnnotationDetails]
) -> list[AnnotationBaseTable]:
    """Create annotations.

    Args:
        session: Database session.
        dataset_id: ID of the dataset.
        annotations: List of AnnotationDetails objects to create.

    Returns:
        List of AnnotationBaseTable objects.
    """
    annotations_to_create = [
        AnnotationCreate(
            sample_id=annotation.sample_id,
            annotation_label_id=annotation.annotation_label_id,
            dataset_id=dataset_id,
            annotation_type=annotation.annotation_type,
            segmentation_mask=annotation.segmentation_mask,
            confidence=annotation.confidence,
            x=annotation.x,
            y=annotation.y,
            width=annotation.width,
            height=annotation.height,
        )
        for annotation in annotations
    ]
    annotation_ids = annotation_resolver.create_many(
        session=session,
        annotations=annotations_to_create,
    )
    return list(annotation_resolver.get_by_ids(session=session, annotation_ids=annotation_ids))


def create_embedding_model(  # noqa: PLR0913
    session: Session,
    dataset_id: UUID,
    embedding_model_name: str = "example_embedding_model",
    embedding_model_hash: str = "example_hash",
    parameter_count_in_mb: int = 100,
    embedding_dimension: int = 128,
) -> EmbeddingModelTable:
    """Helper function to create a embedding model."""
    return embedding_model_resolver.create(
        session=session,
        embedding_model=EmbeddingModelCreate(
            dataset_id=dataset_id,
            name=embedding_model_name,
            embedding_model_hash=embedding_model_hash,
            parameter_count_in_mb=parameter_count_in_mb,
            embedding_dimension=embedding_dimension,
        ),
    )


def create_sample_embedding(
    session: Session,
    sample_id: UUID,
    embedding_model_id: UUID,
    embedding: list[float],
) -> SampleEmbeddingTable:
    """Helper function to create a sample embedding."""
    return sample_embedding_resolver.create(
        session=session,
        sample_embedding=SampleEmbeddingCreate(
            sample_id=sample_id,
            embedding_model_id=embedding_model_id,
            embedding=embedding,
        ),
    )


def create_samples_with_embeddings(
    db_session: Session,
    dataset_id: UUID,
    embedding_model_id: UUID,
    images_and_embeddings: list[tuple[SampleImage, list[float]]],
) -> list[ImageTable]:
    """Creates samples with embeddings in the database.

    Args:
        db_session: The database session.
        dataset_id: The ID of the dataset to add samples to.
        embedding_model_id: The ID of the embedding model.
        images_and_embeddings: A list of tuples, where each tuple contains a
            SampleImage object and its corresponding embedding.

    Returns:
        A list of the created ImageTable objects.
    """
    result = []
    for sample_image, embedding in images_and_embeddings:
        image = create_image(
            session=db_session,
            dataset_id=dataset_id,
            file_path_abs=str(sample_image.path),
            width=sample_image.width,
            height=sample_image.height,
        )
        create_sample_embedding(
            session=db_session,
            sample_id=image.sample_id,
            embedding_model_id=embedding_model_id,
            embedding=embedding,
        )
        result.append(image)
    return result


def fill_db_with_samples_and_embeddings(
    test_db: Session,
    n_samples: int,
    embedding_model_names: list[str],
    embedding_dimension: int = 2,
) -> UUID:
    """Creates a dataset and fills it with sample and embeddings."""
    dataset = create_dataset(test_db)
    embedding_models = []
    for embedding_model_name in embedding_model_names:
        embedding_model = create_embedding_model(
            session=test_db,
            dataset_id=dataset.dataset_id,
            embedding_model_name=embedding_model_name,
        )
        embedding_models.append(embedding_model)
    for i in range(n_samples):
        image = create_image(
            session=test_db,
            dataset_id=dataset.dataset_id,
            file_path_abs=f"sample_{i}.jpg",
        )
        for embedding_model in embedding_models:
            create_sample_embedding(
                session=test_db,
                sample_id=image.sample_id,
                embedding_model_id=embedding_model.embedding_model_id,
                embedding=[i] * embedding_dimension,
            )
    return dataset.dataset_id
