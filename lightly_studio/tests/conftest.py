"""Configuration of the tests."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Generator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel
from sqlalchemy import StaticPool
from sqlmodel import Session

from lightly_studio import db_manager
from lightly_studio.api.app import app
from lightly_studio.db_manager import DatabaseEngine
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
from lightly_studio.models.dataset import DatasetCreate, DatasetTable
from lightly_studio.models.embedding_model import EmbeddingModelCreate
from lightly_studio.models.image import ImageCreate, ImageTable
from lightly_studio.models.tag import TagCreate, TagTable
from lightly_studio.resolvers import (
    annotation_label_resolver,
    annotation_resolver,
    caption_resolver,
    dataset_resolver,
    image_resolver_legacy,
    tag_resolver,
)
from tests.helpers_resolvers import (
    create_annotation_label,
    create_dataset,
    create_image,
)

pytest_plugins = [
    "tests.helpers_resolvers",
]


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Create a test database manager session."""
    test_manager = DatabaseEngine("duckdb:///:memory:", poolclass=StaticPool)
    with test_manager.session() as session:
        yield session


@pytest.fixture
def test_client(db_session: Session) -> Generator[TestClient, None, None]:
    """Test client for API requests."""
    client = TestClient(app)

    def get_session_override() -> Session:
        return db_session

    app.dependency_overrides[db_manager._session_dependency] = get_session_override

    yield client

    app.dependency_overrides.clear()


@pytest.fixture
def dataset(db_session: Session) -> DatasetTable:
    """Create a test dataset."""
    dataset_input = DatasetCreate(name="test_dataset")
    return dataset_resolver.create(db_session, dataset_input)


@pytest.fixture
def dataset_id(datasets: list[DatasetTable]) -> UUID:
    """Return the ID of the first dataset."""
    return datasets[0].dataset_id


@pytest.fixture
def datasets(db_session: Session) -> list[DatasetTable]:
    """Create multiple test datasets."""
    datasets = []
    for i in range(10):
        dataset_input = DatasetCreate(name=f"test_dataset_{i}")
        dataset = dataset_resolver.create(db_session, dataset_input)
        datasets.append(dataset)
    return datasets


@pytest.fixture
def embedding_model_input(dataset: DatasetTable) -> EmbeddingModelCreate:
    """Create an EmbeddingModelCreate instance."""
    return EmbeddingModelCreate(
        dataset_id=dataset.dataset_id,
        embedding_dimension=3,
        name="test_model",
    )


@pytest.fixture
def samples(db_session: Session, dataset: DatasetTable) -> list[ImageTable]:
    """Create test samples."""
    samples = []
    for i in range(10):
        sample_input = ImageCreate(
            file_name=f"test_image_{i}.jpg",
            file_path_abs=f"/test/path/test_image_{i}.jpg",
            width=640,
            height=480,
            dataset_id=dataset.dataset_id,
        )
        sample = image_resolver_legacy.create(db_session, sample_input)
        samples.append(sample)
    return samples


@pytest.fixture
def annotation_label(db_session: Session) -> AnnotationLabelTable:
    """Create a test annotation label."""
    label_input = AnnotationLabelCreate(annotation_label_name="test_label")
    return annotation_label_resolver.create(db_session, label_input)


@pytest.fixture
def annotation_labels(db_session: Session) -> list[AnnotationLabelTable]:
    """Create multiple test annotation labels."""
    labels = []
    for i in range(5):
        label_input = AnnotationLabelCreate(annotation_label_name=f"test_label_{i}")
        label = annotation_label_resolver.create(db_session, label_input)
        labels.append(label)
    return labels


class AnnotationsTestData(BaseModel):
    """Test data for annotations."""

    tags: list[TagTable]
    annotation_labels: list[AnnotationLabelTable]
    datasets: list[DatasetTable]
    annotations: Sequence[AnnotationBaseTable]
    samples: list[ImageTable]

    labeled_annotations: dict[UUID, list[AnnotationBaseTable]] = {}


class CaptionsTestData(BaseModel):
    """Test data for captions."""

    datasets: list[DatasetTable]
    samples: list[ImageTable]

    captions: Sequence[CaptionTable]


def create_test_base_annotation(
    db_session: Session,
    samples: list[ImageTable],
    annotation_label: AnnotationLabelTable,
    annotation_type: AnnotationType = AnnotationType.OBJECT_DETECTION,
) -> AnnotationBaseTable:
    """Create a test object detection annotation input."""
    annotation_base_input = AnnotationCreate(
        sample_id=samples[0].sample_id,
        annotation_type=annotation_type,
        dataset_id=samples[0].dataset_id,
        annotation_label_id=annotation_label.annotation_label_id,
        confidence=0.95,
    )

    annotation_ids = annotation_resolver.create_many(
        db_session,
        [annotation_base_input],
    )

    assert len(annotation_ids) == 1
    annotation = annotation_resolver.get_by_id(db_session, annotation_ids[0])
    assert annotation is not None, "Failed to retrieve the created annotation."
    return annotation


def create_test_base_annotations(
    db_session: Session,
    samples: list[ImageTable],
    annotation_labels: list[AnnotationLabelTable],
    annotation_type: AnnotationType = AnnotationType.OBJECT_DETECTION,
) -> list[AnnotationBaseTable]:
    """Create multiple test object detection annotations."""
    annotation_base_inputs = [
        AnnotationCreate(
            sample_id=sample.sample_id,
            dataset_id=sample.dataset_id,
            annotation_label_id=annotation_labels[i % 2].annotation_label_id,
            annotation_type=annotation_type,
            confidence=0.9 - (i * 0.1),
        )
        for i, sample in enumerate(samples[:3])
    ]
    annotation_ids = annotation_resolver.create_many(
        session=db_session, annotations=annotation_base_inputs
    )
    assert len(annotation_ids) == len(annotation_base_inputs)
    return list(annotation_resolver.get_by_ids(session=db_session, annotation_ids=annotation_ids))


@pytest.fixture
def create_test_data(
    test_db: Session,
) -> tuple[str, str, str]:
    """Create test data for annotation creation tests."""
    # Create dataset
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.dataset_id

    # Create sample
    image = create_image(session=test_db, dataset_id=dataset_id)
    sample_id = image.sample_id

    # Create label
    label = create_annotation_label(session=test_db, annotation_label_name="test_label")
    label_id = label.annotation_label_id

    return dataset_id, sample_id, label_id  # type: ignore[return-value]


@pytest.fixture
def annotation_tags(
    db_session: Session,
    datasets: list[DatasetTable],
) -> list[TagTable]:
    """Create a list of annotation labels for testing."""
    tags = []
    for i in range(4):
        tag = tag_resolver.create(
            db_session,
            TagCreate(
                dataset_id=datasets[i % 2].dataset_id,
                name=f"Test Tag {i}",
                kind="annotation",
            ),
        )
        tags.append(tag)
    return tags


@pytest.fixture
def sample_tags(
    db_session: Session,
    datasets: list[DatasetTable],
) -> list[TagTable]:
    """Create a list of sample tags for testing."""
    tags = []
    for i in range(4):
        tag = tag_resolver.create(
            db_session,
            TagCreate(
                dataset_id=datasets[i % 2].dataset_id,
                name=f"Test Sample Tag {i}",
                kind="sample",
            ),
        )
        tags.append(tag)
    return tags


@pytest.fixture
def samples_assigned_with_tags(
    db_session: Session,
    samples: list[ImageTable],
    sample_tags: list[TagTable],
) -> tuple[list[ImageTable], list[TagTable]]:
    """Create a list of sample tags for testing."""
    assert len(samples) >= 2, "At least 2 samples are required for this fixture."
    assert len(sample_tags) >= 2, "At least 2 sample tags are required for this fixture."
    tag_resolver.add_tag_to_sample(
        session=db_session,
        tag_id=sample_tags[0].tag_id,
        sample=samples[0].sample,
    )
    tag_resolver.add_tag_to_sample(
        session=db_session,
        tag_id=sample_tags[1].tag_id,
        sample=samples[1].sample,
    )
    return samples[:2], sample_tags[:2]


@pytest.fixture
def annotations_test_data(
    db_session: Session,
    datasets: list[DatasetTable],
    samples: list[ImageTable],
    annotation_labels: list[AnnotationLabelTable],
    samples_assigned_with_tags: tuple[list[ImageTable], list[TagTable]],
) -> AnnotationsTestData:
    """Create test data in test database."""
    annotation_types: list[AnnotationType] = [
        AnnotationType.CLASSIFICATION,
        AnnotationType.OBJECT_DETECTION,
        AnnotationType.INSTANCE_SEGMENTATION,
        AnnotationType.SEMANTIC_SEGMENTATION,
    ]

    annotations_to_create: list[AnnotationCreate] = []

    # create annotation for every annotation type
    for _, annotation_type in enumerate(annotation_types):
        # Create 3 annotations for each type
        for i in range(3):
            # We distribute annotation labels across the annotations
            # to ensure that we have different labels for each annotation.
            if len(annotation_labels) < 2:
                raise ValueError("At least 2 annotation labels are required.")
            label_id = annotation_labels[i % 2].annotation_label_id

            annotation = AnnotationCreate(
                annotation_label_id=label_id,
                confidence=0.9 - (i * 0.1),
                dataset_id=datasets[i % 2].dataset_id,
                sample_id=samples[i % 2].sample_id,
                annotation_type=annotation_type,
            )
            if annotation_type == AnnotationType.OBJECT_DETECTION:
                annotation.x = 10
                annotation.y = 20
                annotation.width = 100
                annotation.height = 200

            elif annotation_type == AnnotationType.INSTANCE_SEGMENTATION:
                annotation.x = 15
                annotation.y = 25
                annotation.width = 150
                annotation.height = 250
                annotation.segmentation_mask = [1, 2, 3, 4]
            elif annotation_type == AnnotationType.SEMANTIC_SEGMENTATION:
                annotation.segmentation_mask = [5, 6, 7, 8]

            annotations_to_create.append(annotation)

    annotation_ids = annotation_resolver.create_many(
        session=db_session,
        annotations=annotations_to_create,
    )
    annotations = annotation_resolver.get_by_ids(db_session, annotation_ids)
    labeled_annotations: dict[UUID, list[AnnotationBaseTable]] = {}

    for _annotation in annotations:
        if _annotation.annotation_label_id not in labeled_annotations:
            labeled_annotations[_annotation.annotation_label_id] = []

        labeled_annotations[_annotation.annotation_label_id].append(_annotation)

    return AnnotationsTestData(
        labeled_annotations=labeled_annotations,
        annotations=annotations,
        tags=samples_assigned_with_tags[1],
        annotation_labels=annotation_labels,
        datasets=datasets,
        samples=samples,
    )


@pytest.fixture
def annotation_tags_assigned(
    db_session: Session,
    datasets: list[DatasetTable],
    annotations_test_data: list[AnnotationBaseTable],  # noqa: ARG001
) -> list[TagTable]:
    """Create a list of annotation labels for testing."""
    annotations_all = annotation_resolver.get_all(
        db_session,
    ).annotations

    tags = tag_resolver.get_all_by_dataset_id(db_session, dataset_id=datasets[0].dataset_id)

    # assign the first tag to the 2 annotations
    for i in range(2):
        tag_resolver.assign_tag_to_annotation(
            db_session,
            tags[0],
            annotations_all[i],
        )

    # assign the second tag to the 3 annotations
    for i in range(2, 5):
        tag_resolver.assign_tag_to_annotation(
            db_session,
            tags[1],
            annotations_all[i],
        )

    return tags


@pytest.fixture
def captions_test_data(
    db_session: Session,
    datasets: list[DatasetTable],
    samples: list[ImageTable],
) -> CaptionsTestData:
    """Create test data in test database."""
    captions_to_create: list[CaptionCreate] = []

    # Create 4 captions in the first dataset
    for i in range(4):
        caption = CaptionCreate(
            dataset_id=datasets[0].dataset_id,
            sample_id=samples[0].sample_id,
            text=f"Caption number {i}",
        )

        captions_to_create.append(caption)

    _ = caption_resolver.create_many(
        session=db_session,
        captions=captions_to_create,
    )
    captions_return = caption_resolver.get_all(db_session, datasets[0].dataset_id)

    return CaptionsTestData(
        captions=list(captions_return.captions),
        datasets=datasets,
        samples=samples,
    )


def assert_contains_properties(
    obj: Any,
    expected_props: BaseModel | dict[str, Any],
    float_tolerance: float = 0.01,
) -> None:
    """Assert that obj contains all properties from expected_props."""
    if hasattr(expected_props, "model_dump"):
        expected_dict = expected_props.model_dump()
    else:
        expected_dict = expected_props

    for key, expected_value in expected_dict.items():
        assert hasattr(obj, key), f"Object missing property: {key}"
        actual_value = getattr(obj, key)

        if isinstance(expected_value, float):
            assert actual_value == pytest.approx(expected_value, abs=float_tolerance)
        else:
            assert actual_value == expected_value
