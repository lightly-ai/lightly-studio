from __future__ import annotations

from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_CREATED,
    HTTP_STATUS_NOT_FOUND,
    HTTP_STATUS_OK,
)
from lightly_studio.resolvers import annotation_label_resolver
from tests.helpers_resolvers import create_annotation_label, create_collection


def test_create_annotation_label(db_session: Session, test_client: TestClient) -> None:
    collection_id = create_collection(session=db_session).collection_id
    input_label = {"annotation_label_name": "cat"}

    result = test_client.post(
        f"/api/collections/{collection_id!s}/annotation_labels",
        json=input_label,
    )
    assert result.status_code == HTTP_STATUS_CREATED
    assert result.json()["annotation_label_id"] is not None

    # Check that the label was created in the database
    all_labels = annotation_label_resolver.get_all(
        session=db_session, root_collection_id=collection_id
    )
    assert len(all_labels) == 1
    assert all_labels[0].annotation_label_name == "cat"


def test_get_annotation_labels(db_session: Session, test_client: TestClient) -> None:
    collection_id = create_collection(session=db_session).collection_id
    create_annotation_label(session=db_session, root_collection_id=collection_id, label_name="cat")

    labels_result = test_client.get(f"/api/collections/{collection_id!s}/annotation_labels")
    assert labels_result.status_code == HTTP_STATUS_OK

    assert len(labels_result.json()) == 1
    label = labels_result.json()[0]
    assert label["annotation_label_name"] == "cat"


def test_get_annotation_label(db_session: Session, test_client: TestClient) -> None:
    collection_id = create_collection(session=db_session).collection_id
    label_id = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="cat"
    ).annotation_label_id

    label_result = test_client.get(f"/api/annotation_labels/{label_id!s}")
    assert label_result.status_code == HTTP_STATUS_OK

    label = label_result.json()
    assert label["annotation_label_name"] == "cat"


def test_update_annotation_label(db_session: Session, test_client: TestClient) -> None:
    collection_id = create_collection(session=db_session).collection_id
    label_id = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="cat"
    ).annotation_label_id

    updated_label = {
        "annotation_label_id": str(label_id),
        "annotation_label_name": "dog",
        "root_collection_id": str(collection_id),
    }

    label_result = test_client.put(
        f"/api/annotation_labels/{label_id!s}",
        json=updated_label,
    )
    assert label_result.status_code == HTTP_STATUS_OK

    label = label_result.json()
    assert label["annotation_label_name"] == "dog"


def test_delete_annotation_label(db_session: Session, test_client: TestClient) -> None:
    collection_id = create_collection(session=db_session).collection_id
    label_id = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="cat"
    ).annotation_label_id

    label_result = test_client.delete(f"/api/annotation_labels/{label_id!s}")
    assert label_result.status_code == HTTP_STATUS_OK
    assert label_result.json() == {"status": "deleted"}

    label_result = test_client.get(f"/api/annotation_labels/{label_id!s}")
    assert label_result.status_code == HTTP_STATUS_NOT_FOUND
