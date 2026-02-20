"""Helper functions for tests."""

from __future__ import annotations

import uuid
from collections.abc import Generator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any
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
from lightly_studio.models.caption import CaptionCreate, CaptionTable
from lightly_studio.models.collection import CollectionCreate, CollectionTable, SampleType
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
    caption_resolver,
    collection_resolver,
    embedding_model_resolver,
    image_resolver,
    sample_embedding_resolver,
    tag_resolver,
)
from lightly_studio.type_definitions import PathLike
from tests.resolvers.video import helpers as video_helpers


@pytest.fixture
def test_db() -> Generator[Session, None, None]:
    """Fixture which yields an in-memory database unique to a test."""
    # Setup a test database
    engine = create_engine("duckdb:///:memory:")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        yield session


def create_collection(
    session: Session,
    collection_name: str | None = None,
    parent_collection_id: UUID | None = None,
    sample_type: SampleType = SampleType.IMAGE,
) -> CollectionTable:
    """Helper function to create a collection."""
    if collection_name is None:
        collection_name = f"test_collection_{uuid.uuid4().hex[:8]}"
    return collection_resolver.create(
        session=session,
        collection=CollectionCreate(
            name=collection_name,
            parent_collection_id=parent_collection_id,
            sample_type=sample_type,
        ),
    )


def create_tag(
    session: Session,
    collection_id: UUID,
    tag_name: str = "example_tag",
    kind: TagKind = "sample",
) -> TagTable:
    """Helper function to create a tag."""
    return tag_resolver.create(
        session=session,
        tag=TagCreate(
            collection_id=collection_id,
            name=tag_name,
            kind=kind,
            description="example description",
        ),
    )


def create_image(
    session: Session,
    collection_id: UUID,
    file_path_abs: str = "/path/to/sample1.png",
    width: int = 1920,
    height: int = 1080,
) -> ImageTable:
    """Helper function to create a sample."""
    sample_ids = image_resolver.create_many(
        session=session,
        collection_id=collection_id,
        samples=[
            ImageCreate(
                file_path_abs=file_path_abs,
                file_name=Path(file_path_abs).name,
                width=width,
                height=height,
            )
        ],
    )
    image = image_resolver.get_by_id(session=session, sample_id=sample_ids[0])
    assert image is not None
    return image


@dataclass
class ImageStub:
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
    collection_id: UUID,
    images: list[ImageStub],
) -> list[ImageTable]:
    """Creates samples in the database for a given collection.

    Args:
        db_session: The database session.
        collection_id: The ID of the collection to add samples to.
        images: A list of SampleImage objects representing the samples to create.

    Returns:
        A list of the created ImageTable objects.
    """
    return [
        create_image(
            session=db_session,
            collection_id=collection_id,
            file_path_abs=str(image.path),
            width=image.width,
            height=image.height,
        )
        for image in images
    ]


def create_annotation_label(
    session: Session,
    dataset_id: UUID,
    label_name: str = "cat",
) -> AnnotationLabelTable:
    """Helper function to insert an annotation label."""
    return annotation_label_resolver.create(
        session=session,
        label=AnnotationLabelCreate(
            dataset_id=dataset_id,
            annotation_label_name=label_name,
        ),
    )


def get_annotation_by_type(
    annotations: Sequence[AnnotationBaseTable],
    annotation_type: AnnotationType,
) -> AnnotationBaseTable:
    """Retrieve the first annotation matching the given type."""
    return next(
        annotation for annotation in annotations if annotation.annotation_type == annotation_type
    )


def create_annotation(  # noqa: PLR0913
    session: Session,
    collection_id: UUID,
    sample_id: UUID,
    annotation_label_id: UUID,
    annotation_data: dict[str, Any] | None = None,
    annotation_type: AnnotationType = AnnotationType.OBJECT_DETECTION,
    annotation_collection_name: str | None = None,
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
        parent_collection_id=collection_id,
        annotations=[
            AnnotationCreate(
                parent_sample_id=sample_id,
                annotation_label_id=annotation_label_id,
                annotation_type=annotation_type,
                **(annotation_data),
            )
        ],
        collection_name=annotation_collection_name,
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
    session: Session, collection_id: UUID, annotations: list[AnnotationDetails]
) -> list[AnnotationBaseTable]:
    """Create annotations.

    Args:
        session: Database session.
        collection_id: ID of the collection.
        annotations: List of AnnotationDetails objects to create.

    Returns:
        List of AnnotationBaseTable objects.
    """
    annotations_to_create = [
        AnnotationCreate(
            parent_sample_id=annotation.sample_id,
            annotation_label_id=annotation.annotation_label_id,
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
        parent_collection_id=collection_id,
        annotations=annotations_to_create,
    )
    return list(annotation_resolver.get_by_ids(session=session, annotation_ids=annotation_ids))


def create_embedding_model(  # noqa: PLR0913
    session: Session,
    collection_id: UUID,
    embedding_model_name: str = "example_embedding_model",
    embedding_model_hash: str = "example_hash",
    parameter_count_in_mb: int = 100,
    embedding_dimension: int = 128,
) -> EmbeddingModelTable:
    """Helper function to create a embedding model."""
    return embedding_model_resolver.create(
        session=session,
        embedding_model=EmbeddingModelCreate(
            collection_id=collection_id,
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
    session: Session,
    collection_id: UUID,
    embedding_model_id: UUID,
    images_and_embeddings: list[tuple[ImageStub, list[float]]],
) -> list[ImageTable]:
    """Creates samples with embeddings in the database.

    Args:
        session: The database session.
        collection_id: The ID of the collection to add samples to.
        embedding_model_id: The ID of the embedding model.
        images_and_embeddings: A list of tuples, where each tuple contains a
            SampleImage object and its corresponding embedding.

    Returns:
        A list of the created ImageTable objects.
    """
    result = []
    for sample_image, embedding in images_and_embeddings:
        image = create_image(
            session=session,
            collection_id=collection_id,
            file_path_abs=str(sample_image.path),
            width=sample_image.width,
            height=sample_image.height,
        )
        create_sample_embedding(
            session=session,
            sample_id=image.sample_id,
            embedding_model_id=embedding_model_id,
            embedding=embedding,
        )
        result.append(image)
    return result


def create_caption(
    session: Session,
    # TODO(Michal, 12/2025): Get collection_id from the parent sample and remove it from here.
    collection_id: UUID,
    parent_sample_id: UUID,
    text: str = "test caption",
) -> CaptionTable:
    """Helper function to create a caption."""
    sample_ids = caption_resolver.create_many(
        session=session,
        parent_collection_id=collection_id,
        captions=[
            CaptionCreate(
                parent_sample_id=parent_sample_id,
                text=text,
            )
        ],
    )
    caption = caption_resolver.get_by_ids(session=session, sample_ids=sample_ids)
    assert len(caption) == 1
    return caption[0]


def fill_db_with_samples_and_embeddings(
    test_db: Session,
    n_samples: int,
    embedding_model_names: list[str],
    embedding_dimension: int = 2,
) -> UUID:
    """Creates a collection and fills it with sample and embeddings."""
    collection = create_collection(test_db)
    embedding_models = []
    for embedding_model_name in embedding_model_names:
        embedding_model = create_embedding_model(
            session=test_db,
            collection_id=collection.collection_id,
            embedding_model_name=embedding_model_name,
        )
        embedding_models.append(embedding_model)
    for i in range(n_samples):
        image = create_image(
            session=test_db,
            collection_id=collection.collection_id,
            file_path_abs=f"sample_{i}.jpg",
        )
        for embedding_model in embedding_models:
            create_sample_embedding(
                session=test_db,
                sample_id=image.sample_id,
                embedding_model_id=embedding_model.embedding_model_id,
                embedding=[i] * embedding_dimension,
            )
    return collection.collection_id


def fill_db_with_video_samples_and_embeddings(
    test_db: Session,
    n_samples: int,
    embedding_model_names: list[str],
    embedding_dimension: int = 2,
) -> UUID:
    """Create a video collection and fill it with video samples and embeddings.

    Args:
        test_db: Database session for the test.
        n_samples: Number of video samples to create.
        embedding_model_names: Names of embedding models to create and attach to each sample.
        embedding_dimension: Dimension of each embedding vector. Defaults to 2.

    Returns:
        The collection_id of the created video collection.
    """
    collection = create_collection(session=test_db, sample_type=SampleType.VIDEO)
    embedding_models = []
    for embedding_model_name in embedding_model_names:
        embedding_model = create_embedding_model(
            session=test_db,
            collection_id=collection.collection_id,
            embedding_model_name=embedding_model_name,
        )
        embedding_models.append(embedding_model)
    for i in range(n_samples):
        video = video_helpers.create_video(
            session=test_db,
            collection_id=collection.collection_id,
            video=video_helpers.VideoStub(path=f"/path/to/sample_{i}.mp4"),
        )
        for embedding_model in embedding_models:
            create_sample_embedding(
                session=test_db,
                sample_id=video.sample_id,
                embedding_model_id=embedding_model.embedding_model_id,
                embedding=[i] * embedding_dimension,
            )
    return collection.collection_id
