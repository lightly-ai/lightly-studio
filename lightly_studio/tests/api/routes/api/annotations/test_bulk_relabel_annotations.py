from __future__ import annotations

from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_OK,
    HTTP_STATUS_UNPROCESSABLE_ENTITY,
)
from lightly_studio.resolvers import annotation_resolver
from tests.helpers_resolvers import (
    AnnotationDetails,
    create_annotation_label,
    create_annotations,
    create_collection,
    create_image,
)


def test_bulk_relabel_annotations(db_session: Session, test_client: TestClient) -> None:
    annotation_collection_id, _, annotation_ids = _create_cat_cat_dog_annotations(
        session=db_session
    )

    response = test_client.post(
        f"/api/collections/{annotation_collection_id}/annotations/bulk_relabel",
        json={
            "annotation_ids": [str(annotation_ids[0]), str(annotation_ids[2])],
            "label_name": "bird",
        },
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {
        "previous_labels": [
            {"annotation_id": str(annotation_ids[0]), "label_name": "cat"},
            {"annotation_id": str(annotation_ids[2]), "label_name": "dog"},
        ]
    }
    assert _get_label_names(session=db_session, annotation_ids=annotation_ids) == [
        "bird",
        "cat",
        "bird",
    ]


def test_bulk_relabel_annotations__ignores_missing_id(
    db_session: Session, test_client: TestClient
) -> None:
    annotation_collection_id, _, annotation_ids = _create_cat_cat_dog_annotations(
        session=db_session
    )

    response = test_client.post(
        f"/api/collections/{annotation_collection_id}/annotations/bulk_relabel",
        json={"annotation_ids": [str(annotation_ids[2]), str(uuid4())], "label_name": "cat"},
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {
        "previous_labels": [{"annotation_id": str(annotation_ids[2]), "label_name": "dog"}]
    }
    assert _get_label_names(session=db_session, annotation_ids=annotation_ids) == [
        "cat",
        "cat",
        "cat",
    ]


def test_bulk_relabel_annotations__empty_ids(db_session: Session, test_client: TestClient) -> None:
    annotation_collection_id, _, _ = _create_cat_cat_dog_annotations(session=db_session)

    response = test_client.post(
        f"/api/collections/{annotation_collection_id}/annotations/bulk_relabel",
        json={"annotation_ids": [], "label_name": "bird"},
    )

    assert response.status_code == HTTP_STATUS_UNPROCESSABLE_ENTITY


def test_bulk_relabel_annotations_by_filter(db_session: Session, test_client: TestClient) -> None:
    annotation_collection_id, cat_label_id, annotation_ids = _create_cat_cat_dog_annotations(
        session=db_session
    )

    response = test_client.post(
        f"/api/collections/{annotation_collection_id}/annotations/bulk_relabel_by_filter",
        json={
            "filter": {
                "filter_type": "annotations",
                "annotation_label_ids": [str(cat_label_id)],
            },
            "label_name": "bird",
        },
    )

    assert response.status_code == HTTP_STATUS_OK
    previous_labels = response.json()["previous_labels"]
    assert sorted(previous_labels, key=lambda label: label["annotation_id"]) == sorted(
        [
            {"annotation_id": str(annotation_ids[0]), "label_name": "cat"},
            {"annotation_id": str(annotation_ids[1]), "label_name": "cat"},
        ],
        key=lambda label: label["annotation_id"],
    )
    assert _get_label_names(session=db_session, annotation_ids=annotation_ids) == [
        "bird",
        "bird",
        "dog",
    ]


def test_bulk_relabel_annotations_by_filter__keeps_other_annotation_collection(
    db_session: Session, test_client: TestClient
) -> None:
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    label = create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="cat"
    )
    annotation_details = [
        AnnotationDetails(sample_id=image.sample_id, annotation_label_id=label.annotation_label_id)
    ]
    gt_annotation = create_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        annotations=annotation_details,
        collection_name="ground_truth",
    )[0]
    gt_annotation_id = gt_annotation.sample_id
    pred_annotation_id = create_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        annotations=annotation_details,
        collection_name="predictions",
    )[0].sample_id

    response = test_client.post(
        f"/api/collections/{gt_annotation.annotation_collection_id}/annotations/bulk_relabel_by_filter",
        json={
            "filter": {
                "filter_type": "annotations",
                "annotation_label_ids": [str(label.annotation_label_id)],
            },
            "label_name": "dog",
        },
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {
        "previous_labels": [{"annotation_id": str(gt_annotation_id), "label_name": "cat"}]
    }
    assert _get_label_names(
        session=db_session, annotation_ids=[gt_annotation_id, pred_annotation_id]
    ) == ["dog", "cat"]


def test_bulk_relabel_annotations_by_filter__rejects_non_annotation_filter(
    db_session: Session, test_client: TestClient
) -> None:
    annotation_collection_id, _, annotation_ids = _create_cat_cat_dog_annotations(
        session=db_session
    )

    response = test_client.post(
        f"/api/collections/{annotation_collection_id}/annotations/bulk_relabel_by_filter",
        json={"filter": {"filter_type": "image"}, "label_name": "bird"},
    )

    assert response.status_code == HTTP_STATUS_UNPROCESSABLE_ENTITY
    assert _get_label_names(session=db_session, annotation_ids=annotation_ids) == [
        "cat",
        "cat",
        "dog",
    ]


def _create_cat_cat_dog_annotations(session: Session) -> tuple[UUID, UUID, list[UUID]]:
    """Create two cat and one dog annotation in a new annotation collection.

    Returns:
        The annotation collection ID, the cat label ID and the annotation IDs.
    """
    collection = create_collection(session=session)
    image = create_image(session=session, collection_id=collection.collection_id)
    cat_label = create_annotation_label(
        session=session, root_collection_id=collection.collection_id, label_name="cat"
    )
    dog_label = create_annotation_label(
        session=session, root_collection_id=collection.collection_id, label_name="dog"
    )
    annotations = create_annotations(
        session=session,
        collection_id=collection.collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=image.sample_id, annotation_label_id=cat_label.annotation_label_id
            ),
            AnnotationDetails(
                sample_id=image.sample_id, annotation_label_id=cat_label.annotation_label_id
            ),
            AnnotationDetails(
                sample_id=image.sample_id, annotation_label_id=dog_label.annotation_label_id
            ),
        ],
        collection_name="ground_truth",
    )
    return (
        annotations[0].annotation_collection_id,
        cat_label.annotation_label_id,
        [annotation.sample_id for annotation in annotations],
    )


def _get_label_names(session: Session, annotation_ids: list[UUID]) -> list[str]:
    return [
        annotation.annotation_label.annotation_label_name
        for annotation in annotation_resolver.get_by_ids(
            session=session, annotation_ids=annotation_ids
        )
    ]
