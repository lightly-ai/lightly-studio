from __future__ import annotations

import sys
from uuid import UUID

import pytest
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.collection import CollectionTable, SampleType
from lightly_studio.models.image import ImageTable
from lightly_studio.resolvers import (
    annotation_label_resolver,
    annotation_resolver,
    collection_resolver,
)
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.services import annotations_service
from tests.helpers_resolvers import (
    ImageStub,
    create_annotation,
    create_annotation_label,
    create_collection,
    create_images,
)


@pytest.fixture
def collection(db_session: Session) -> CollectionTable:
    return create_collection(session=db_session)


@pytest.fixture
def images(db_session: Session, collection: CollectionTable) -> list[ImageTable]:
    return create_images(
        db_session=db_session,
        collection_id=collection.collection_id,
        images=[ImageStub(path=f"image_{i}.png") for i in range(3)],
    )


def test_create_classification_annotations(
    db_session: Session, collection: CollectionTable, images: list[ImageTable]
) -> None:
    result = annotations_service.create_classification_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        class_name="cat",
        sample_ids=[image.sample_id for image in images],
    )

    assert result.created_count == 3
    assert result.skipped_count == 0
    assert len(result.created_annotation_ids) == 3
    assert _class_names_by_sample_id(session=db_session, images=images) == {
        image.sample_id: {"cat"} for image in images
    }


def test_create_classification_annotations__creates_only_classifications(
    db_session: Session, collection: CollectionTable, images: list[ImageTable]
) -> None:
    result = annotations_service.create_classification_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        class_name="cat",
        sample_ids=[images[0].sample_id],
    )

    annotation = annotation_resolver.get_by_id(
        session=db_session, annotation_id=result.created_annotation_ids[0]
    )
    assert annotation is not None
    assert annotation.annotation_type == AnnotationType.CLASSIFICATION
    assert annotation.object_detection_details is None
    assert annotation.segmentation_details is None


def test_create_classification_annotations__creates_annotation_class_on_the_fly(
    db_session: Session, collection: CollectionTable, images: list[ImageTable]
) -> None:
    annotations_service.create_classification_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        class_name="brand_new",
        sample_ids=[images[0].sample_id],
    )

    label = annotation_label_resolver.get_by_label_name(
        session=db_session, dataset_id=collection.dataset_id, label_name="brand_new"
    )
    assert label is not None


def test_create_classification_annotations__reuses_existing_annotation_class(
    db_session: Session, collection: CollectionTable, images: list[ImageTable]
) -> None:
    existing = create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="cat"
    )

    result = annotations_service.create_classification_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        class_name="cat",
        sample_ids=[images[0].sample_id],
    )

    annotation = annotation_resolver.get_by_id(
        session=db_session, annotation_id=result.created_annotation_ids[0]
    )
    assert annotation is not None
    assert annotation.annotation_label_id == existing.annotation_label_id


def test_create_classification_annotations__skips_samples_that_already_have_the_class(
    db_session: Session, collection: CollectionTable, images: list[ImageTable]
) -> None:
    label = create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="cat"
    )
    existing = create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=images[0].sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.CLASSIFICATION,
        annotation_data={},
    )

    result = annotations_service.create_classification_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        class_name="cat",
        sample_ids=[image.sample_id for image in images],
    )

    assert result.created_count == 2
    assert result.skipped_count == 1
    assert existing.sample_id not in result.created_annotation_ids
    assert _class_names_by_sample_id(session=db_session, images=images) == {
        image.sample_id: {"cat"} for image in images
    }


def test_create_classification_annotations__rerun_creates_nothing(
    db_session: Session, collection: CollectionTable, images: list[ImageTable]
) -> None:
    sample_ids = [image.sample_id for image in images]
    annotations_service.create_classification_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        class_name="cat",
        sample_ids=sample_ids,
    )

    result = annotations_service.create_classification_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        class_name="cat",
        sample_ids=sample_ids,
    )

    assert result.created_count == 0
    assert result.skipped_count == 3


def test_create_classification_annotations__duplicate_sample_ids_annotated_once(
    db_session: Session, collection: CollectionTable, images: list[ImageTable]
) -> None:
    result = annotations_service.create_classification_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        class_name="cat",
        sample_ids=[images[0].sample_id, images[0].sample_id],
    )

    assert result.created_count == 1
    assert result.skipped_count == 0


def test_create_classification_annotations__adds_second_class_alongside_first(
    db_session: Session, collection: CollectionTable, images: list[ImageTable]
) -> None:
    annotations_service.create_classification_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        class_name="cat",
        sample_ids=[images[0].sample_id],
    )

    result = annotations_service.create_classification_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        class_name="dog",
        sample_ids=[images[0].sample_id],
    )

    assert result.created_count == 1
    assert result.skipped_count == 0
    assert _class_names_by_sample_id(session=db_session, images=images[:1]) == {
        images[0].sample_id: {"cat", "dog"}
    }


def test_create_classification_annotations__default_annotation_collection(
    db_session: Session, collection: CollectionTable, images: list[ImageTable]
) -> None:
    result = annotations_service.create_classification_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        class_name="cat",
        sample_ids=[images[0].sample_id],
    )

    default_collection_id = collection_resolver.get_by_name(
        session=db_session,
        name=SampleType.ANNOTATION.value.lower(),
        parent_collection_id=collection.collection_id,
    )
    assert (
        _annotation_collection_id(
            session=db_session, annotation_id=result.created_annotation_ids[0]
        )
        == default_collection_id
    )


def test_create_classification_annotations__named_annotation_collection(
    db_session: Session, collection: CollectionTable, images: list[ImageTable]
) -> None:
    result = annotations_service.create_classification_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        class_name="cat",
        sample_ids=[images[0].sample_id],
        annotation_collection_name="ground_truth",
    )

    named_collection_id = collection_resolver.get_by_name(
        session=db_session,
        name="ground_truth",
        parent_collection_id=collection.collection_id,
    )
    assert named_collection_id is not None
    assert (
        _annotation_collection_id(
            session=db_session, annotation_id=result.created_annotation_ids[0]
        )
        == named_collection_id
    )


def test_create_classification_annotations__dedupe_is_per_annotation_collection(
    db_session: Session, collection: CollectionTable, images: list[ImageTable]
) -> None:
    annotations_service.create_classification_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        class_name="cat",
        sample_ids=[images[0].sample_id],
        annotation_collection_name="ground_truth",
    )

    result = annotations_service.create_classification_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        class_name="cat",
        sample_ids=[images[0].sample_id],
        annotation_collection_name="predictions",
    )

    assert result.created_count == 1
    assert result.skipped_count == 0


def test_create_classification_annotations__batches(
    db_session: Session,
    collection: CollectionTable,
    mocker: MockerFixture,
) -> None:
    # The service package re-exports the function under the module's own name, so the
    # module has to be looked up in sys.modules to patch its constant.
    service_module = sys.modules[
        "lightly_studio.services.annotations_service.create_classification_annotations"
    ]
    mocker.patch.object(service_module, "CREATE_BATCH_SIZE", 2)
    images = create_images(
        db_session=db_session,
        collection_id=collection.collection_id,
        images=[ImageStub(path=f"batched_{i}.png") for i in range(5)],
    )

    result = annotations_service.create_classification_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        class_name="cat",
        sample_ids=[image.sample_id for image in images],
    )

    assert result.created_count == 5
    assert len(set(result.created_annotation_ids)) == 5


def test_create_classification_annotations_by_filter(
    db_session: Session, collection: CollectionTable, images: list[ImageTable]
) -> None:
    result = annotations_service.create_classification_annotations_by_filter(
        session=db_session,
        collection_id=collection.collection_id,
        class_name="cat",
        grid_filter=ImageFilter(),
    )

    assert result.created_count == 3
    assert result.skipped_count == 0
    assert _class_names_by_sample_id(session=db_session, images=images) == {
        image.sample_id: {"cat"} for image in images
    }


def test_create_classification_annotations_by_filter__matches_subset(
    db_session: Session, collection: CollectionTable
) -> None:
    wide, narrow = create_images(
        db_session=db_session,
        collection_id=collection.collection_id,
        images=[
            ImageStub(path="wide.png", width=1920, height=1080),
            ImageStub(path="narrow.png", width=10, height=10),
        ],
    )

    result = annotations_service.create_classification_annotations_by_filter(
        session=db_session,
        collection_id=collection.collection_id,
        class_name="cat",
        grid_filter=ImageFilter.model_validate({"width": {"min": 100}}),
    )

    assert result.created_count == 1
    assert _class_names_by_sample_id(session=db_session, images=[wide, narrow]) == {
        wide.sample_id: {"cat"},
        narrow.sample_id: set(),
    }


def test_create_classification_annotations_by_filter__skips_already_annotated(
    db_session: Session, collection: CollectionTable, images: list[ImageTable]
) -> None:
    annotations_service.create_classification_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        class_name="cat",
        sample_ids=[images[0].sample_id],
    )

    result = annotations_service.create_classification_annotations_by_filter(
        session=db_session,
        collection_id=collection.collection_id,
        class_name="cat",
        grid_filter=ImageFilter(),
    )

    assert result.created_count == 2
    assert result.skipped_count == 1


def _class_names_by_sample_id(session: Session, images: list[ImageTable]) -> dict[UUID, set[str]]:
    annotations = annotation_resolver.get_all_by_parent_sample_ids(
        session=session, parent_sample_ids=[image.sample_id for image in images]
    )
    class_names: dict[UUID, set[str]] = {image.sample_id: set() for image in images}
    for annotation in annotations:
        class_names[annotation.parent_sample_id].add(
            annotation.annotation_label.annotation_label_name
        )
    return class_names


def _annotation_collection_id(session: Session, annotation_id: UUID) -> UUID:
    annotation = annotation_resolver.get_by_id(session=session, annotation_id=annotation_id)
    assert annotation is not None
    return annotation.sample.collection_id
