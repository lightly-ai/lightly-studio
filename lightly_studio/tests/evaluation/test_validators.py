"""Tests for evaluation validators."""

from __future__ import annotations

import uuid

import pytest
from pytest_mock import MockerFixture

from lightly_studio.core.image.image_dataset import ImageDataset
from lightly_studio.evaluation.validators import (
    _validate_annotation_collection,
    _validate_collection_annotation_type,
    resolve_and_validate_collection,
)
from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.collection import SampleType
from lightly_studio.models.evaluation_run import EvaluationTaskType
from lightly_studio.resolvers import collection_resolver
from tests.helpers_resolvers import create_annotation, create_annotation_label, create_image


def test_assert_collection_annotation_type__passes_for_empty_collection(
    patch_collection: None,  # noqa: ARG001
) -> None:
    dataset = ImageDataset.create(name="test_dataset")
    collection_id = collection_resolver.get_or_create_child_collection(
        session=dataset.session,
        collection_id=dataset.collection_id,
        sample_type=SampleType.ANNOTATION,
        name="gt",
    )
    _validate_collection_annotation_type(
        session=dataset.session,
        collection_id=collection_id,
        expected_type=AnnotationType.OBJECT_DETECTION,
    )


def test_assert_collection_annotation_type__passes_when_all_annotations_match(
    patch_collection: None,  # noqa: ARG001
) -> None:
    dataset = ImageDataset.create(name="test_dataset")
    label = create_annotation_label(
        session=dataset.session, root_collection_id=dataset.collection_id
    )
    image = create_image(session=dataset.session, collection_id=dataset.collection_id)
    collection_id = collection_resolver.get_or_create_child_collection(
        session=dataset.session,
        collection_id=dataset.collection_id,
        sample_type=SampleType.ANNOTATION,
        name="gt",
    )
    create_annotation(
        session=dataset.session,
        collection_id=dataset.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.OBJECT_DETECTION,
        annotation_collection_name="gt",
    )
    _validate_collection_annotation_type(
        session=dataset.session,
        collection_id=collection_id,
        expected_type=AnnotationType.OBJECT_DETECTION,
    )


def test_assert_collection_annotation_type__raises_on_type_mismatch(
    patch_collection: None,  # noqa: ARG001
) -> None:
    dataset = ImageDataset.create(name="test_dataset")
    label = create_annotation_label(
        session=dataset.session, root_collection_id=dataset.collection_id
    )
    image = create_image(session=dataset.session, collection_id=dataset.collection_id)
    collection_id = collection_resolver.get_or_create_child_collection(
        session=dataset.session,
        collection_id=dataset.collection_id,
        sample_type=SampleType.ANNOTATION,
        name="gt",
    )
    create_annotation(
        session=dataset.session,
        collection_id=dataset.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.CLASSIFICATION,
        annotation_collection_name="gt",
    )
    with pytest.raises(ValueError, match="object_detection"):
        _validate_collection_annotation_type(
            session=dataset.session,
            collection_id=collection_id,
            expected_type=AnnotationType.OBJECT_DETECTION,
        )


def test__validate_annotation_collection__raises_when_collection_not_found(
    patch_collection: None,  # noqa: ARG001
) -> None:
    dataset = ImageDataset.create(name="test_dataset")
    missing_id = uuid.uuid4()
    with pytest.raises(ValueError, match=str(missing_id)):
        _validate_annotation_collection(session=dataset.session, collection_id=missing_id)


def test__validate_annotation_collection__raises_on_wrong_sample_type(
    patch_collection: None,  # noqa: ARG001
) -> None:
    dataset = ImageDataset.create(name="test_dataset")
    image_collection_id = collection_resolver.get_or_create_child_collection(
        session=dataset.session,
        collection_id=dataset.collection_id,
        sample_type=SampleType.IMAGE,
        name="images",
    )
    with pytest.raises(ValueError, match="annotation"):
        _validate_annotation_collection(session=dataset.session, collection_id=image_collection_id)


def test__validate_annotation_collection__passes_for_annotation_collection(
    patch_collection: None,  # noqa: ARG001
) -> None:
    dataset = ImageDataset.create(name="test_dataset")
    annotation_collection_id = collection_resolver.get_or_create_child_collection(
        session=dataset.session,
        collection_id=dataset.collection_id,
        sample_type=SampleType.ANNOTATION,
        name="gt",
    )
    _validate_annotation_collection(session=dataset.session, collection_id=annotation_collection_id)


def test_resolve_and_validate_collection__passes(
    patch_collection: None,  # noqa: ARG001
) -> None:
    dataset = ImageDataset.create(name="test_dataset")
    collection_resolver.get_or_create_child_collection(
        session=dataset.session,
        collection_id=dataset.collection_id,
        sample_type=SampleType.ANNOTATION,
        name="gt",
    )
    collection_id = resolve_and_validate_collection(
        session=dataset.session,
        collection_id=dataset.collection_id,
        collection_name="gt",
        task_type=EvaluationTaskType.OBJECT_DETECTION,
    )
    assert collection_id is not None


def test_resolve_and_validate_collection__raises_when_not_found(
    patch_collection: None,  # noqa: ARG001
) -> None:
    dataset = ImageDataset.create(name="test_dataset")
    with pytest.raises(ValueError, match="'gt'"):
        resolve_and_validate_collection(
            session=dataset.session,
            collection_id=dataset.collection_id,
            collection_name="gt",
            task_type=EvaluationTaskType.OBJECT_DETECTION,
        )


def test_resolve_and_validate_collection__raises_when_wrong_sample_type(
    patch_collection: None,  # noqa: ARG001
) -> None:
    dataset = ImageDataset.create(name="test_dataset")
    collection_resolver.get_or_create_child_collection(
        session=dataset.session,
        collection_id=dataset.collection_id,
        sample_type=SampleType.IMAGE,
        name="gt",
    )
    with pytest.raises(ValueError, match="annotation"):
        resolve_and_validate_collection(
            session=dataset.session,
            collection_id=dataset.collection_id,
            collection_name="gt",
            task_type=EvaluationTaskType.OBJECT_DETECTION,
        )


def test_resolve_and_validate_collection__raises_on_unsupported_task_type(
    patch_collection: None,  # noqa: ARG001
    mocker: MockerFixture,
) -> None:
    dataset = ImageDataset.create(name="test_dataset")
    unsupported_task_type = mocker.MagicMock(spec=EvaluationTaskType)
    with pytest.raises(ValueError, match="Unsupported evaluation task type"):
        resolve_and_validate_collection(
            session=dataset.session,
            collection_id=dataset.collection_id,
            collection_name="gt",
            task_type=unsupported_task_type,
        )
