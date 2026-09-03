from __future__ import annotations

from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.api.routes.api.status import HTTP_STATUS_CREATED
from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.collection import CollectionTable, SampleType
from lightly_studio.models.image import ImageTable
from lightly_studio.resolvers import annotation_resolver, collection_resolver
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
    db_session: Session,
    test_client: TestClient,
    collection: CollectionTable,
    images: list[ImageTable],
) -> None:
    response = test_client.post(
        _bulk_route(collection),
        json={
            "sample_ids": [str(image.sample_id) for image in images],
            "class_name": "cat",
        },
    )

    assert response.status_code == HTTP_STATUS_CREATED
    body = response.json()
    assert body["created_count"] == 3
    assert body["skipped_count"] == 0
    assert len(body["created_annotation_ids"]) == 3
    assert _class_names_by_sample_id(session=db_session, images=images) == {
        image.sample_id: {"cat"} for image in images
    }


def test_create_classification_annotations__skips_already_annotated(
    db_session: Session,
    test_client: TestClient,
    collection: CollectionTable,
    images: list[ImageTable],
) -> None:
    label = create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="cat"
    )
    create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=images[0].sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.CLASSIFICATION,
        annotation_data={},
    )

    response = test_client.post(
        _bulk_route(collection),
        json={
            "sample_ids": [str(image.sample_id) for image in images],
            "class_name": "cat",
        },
    )

    assert response.status_code == HTTP_STATUS_CREATED
    assert response.json()["created_count"] == 2
    assert response.json()["skipped_count"] == 1


def test_create_classification_annotations__adds_second_class_alongside_first(
    db_session: Session,
    test_client: TestClient,
    collection: CollectionTable,
    images: list[ImageTable],
) -> None:
    route = _bulk_route(collection)
    body = {"sample_ids": [str(images[0].sample_id)]}

    test_client.post(route, json={**body, "class_name": "cat"})
    response = test_client.post(route, json={**body, "class_name": "dog"})

    assert response.status_code == HTTP_STATUS_CREATED
    assert response.json()["created_count"] == 1
    assert _class_names_by_sample_id(session=db_session, images=images[:1]) == {
        images[0].sample_id: {"cat", "dog"}
    }


def test_create_classification_annotations__creates_annotation_class_on_the_fly(
    db_session: Session,
    test_client: TestClient,
    collection: CollectionTable,
    images: list[ImageTable],
) -> None:
    response = test_client.post(
        _bulk_route(collection),
        json={"sample_ids": [str(images[0].sample_id)], "class_name": "brand_new"},
    )

    assert response.status_code == HTTP_STATUS_CREATED
    assert _class_names_by_sample_id(session=db_session, images=images[:1]) == {
        images[0].sample_id: {"brand_new"}
    }


def test_create_classification_annotations__default_annotation_collection(
    db_session: Session,
    test_client: TestClient,
    collection: CollectionTable,
    images: list[ImageTable],
) -> None:
    response = test_client.post(
        _bulk_route(collection),
        json={"sample_ids": [str(images[0].sample_id)], "class_name": "cat"},
    )

    assert response.status_code == HTTP_STATUS_CREATED
    assert _annotation_collection_ids(session=db_session, response_body=response.json()) == {
        collection_resolver.get_by_name(
            session=db_session,
            name=SampleType.ANNOTATION.value.lower(),
            parent_collection_id=collection.collection_id,
        )
    }


def test_create_classification_annotations__named_annotation_collection(
    db_session: Session,
    test_client: TestClient,
    collection: CollectionTable,
    images: list[ImageTable],
) -> None:
    response = test_client.post(
        _bulk_route(collection),
        json={
            "sample_ids": [str(images[0].sample_id)],
            "class_name": "cat",
            "annotation_collection_name": "ground_truth",
        },
    )

    assert response.status_code == HTTP_STATUS_CREATED
    named_collection_id = collection_resolver.get_by_name(
        session=db_session,
        name="ground_truth",
        parent_collection_id=collection.collection_id,
    )
    assert named_collection_id is not None
    assert _annotation_collection_ids(session=db_session, response_body=response.json()) == {
        named_collection_id
    }


def test_create_classification_annotations_by_filter(
    db_session: Session,
    test_client: TestClient,
    collection: CollectionTable,
    images: list[ImageTable],
) -> None:
    response = test_client.post(
        _bulk_by_filter_route(collection),
        json={"filter": {"filter_type": "image"}, "class_name": "cat"},
    )

    assert response.status_code == HTTP_STATUS_CREATED
    assert response.json()["created_count"] == 3
    assert _class_names_by_sample_id(session=db_session, images=images) == {
        image.sample_id: {"cat"} for image in images
    }


def test_create_classification_annotations_by_filter__matches_id_list_result(
    db_session: Session,
    test_client: TestClient,
    collection: CollectionTable,
    images: list[ImageTable],
) -> None:
    by_ids = test_client.post(
        _bulk_route(collection),
        json={"sample_ids": [str(image.sample_id) for image in images], "class_name": "cat"},
    )
    by_filter = test_client.post(
        _bulk_by_filter_route(collection),
        json={"filter": {"filter_type": "image"}, "class_name": "dog"},
    )

    assert by_ids.json()["created_count"] == by_filter.json()["created_count"]
    assert by_ids.json()["skipped_count"] == by_filter.json()["skipped_count"]
    assert _class_names_by_sample_id(session=db_session, images=images) == {
        image.sample_id: {"cat", "dog"} for image in images
    }


def test_create_classification_annotations_by_filter__matches_subset(
    db_session: Session,
    test_client: TestClient,
    collection: CollectionTable,
) -> None:
    wide, narrow = create_images(
        db_session=db_session,
        collection_id=collection.collection_id,
        images=[
            ImageStub(path="wide.png", width=1920, height=1080),
            ImageStub(path="narrow.png", width=10, height=10),
        ],
    )

    response = test_client.post(
        _bulk_by_filter_route(collection),
        json={
            "filter": {"filter_type": "image", "width": {"min": 100}},
            "class_name": "cat",
        },
    )

    assert response.status_code == HTTP_STATUS_CREATED
    assert response.json()["created_count"] == 1
    assert _class_names_by_sample_id(session=db_session, images=[wide, narrow]) == {
        wide.sample_id: {"cat"},
        narrow.sample_id: set(),
    }


@pytest.mark.usefixtures("images")
def test_create_classification_annotations_by_filter__named_annotation_collection(
    db_session: Session,
    test_client: TestClient,
    collection: CollectionTable,
) -> None:
    response = test_client.post(
        _bulk_by_filter_route(collection),
        json={
            "filter": {"filter_type": "image"},
            "class_name": "cat",
            "annotation_collection_name": "ground_truth",
        },
    )

    assert response.status_code == HTTP_STATUS_CREATED
    named_collection_id = collection_resolver.get_by_name(
        session=db_session,
        name="ground_truth",
        parent_collection_id=collection.collection_id,
    )
    assert named_collection_id is not None
    assert _annotation_collection_ids(session=db_session, response_body=response.json()) == {
        named_collection_id
    }


def _bulk_route(collection: CollectionTable) -> str:
    return f"/api/collections/{collection.collection_id!s}/annotations/classifications/bulk"


def _bulk_by_filter_route(collection: CollectionTable) -> str:
    return (
        f"/api/collections/{collection.collection_id!s}/annotations/classifications/bulk_by_filter"
    )


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


def _annotation_collection_ids(session: Session, response_body: dict[str, object]) -> set[UUID]:
    annotation_ids = response_body["created_annotation_ids"]
    assert isinstance(annotation_ids, list)
    annotations = annotation_resolver.get_by_ids(
        session=session, annotation_ids=[UUID(annotation_id) for annotation_id in annotation_ids]
    )
    return {annotation.sample.collection_id for annotation in annotations}
