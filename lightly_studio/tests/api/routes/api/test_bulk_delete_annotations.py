from __future__ import annotations

from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.api.routes.api.status import HTTP_STATUS_BAD_REQUEST, HTTP_STATUS_OK
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.collection import SampleType
from lightly_studio.models.sample import SampleTable
from tests.helpers_resolvers import (
    AnnotationDetails,
    ImageStub,
    create_annotation_label,
    create_annotations,
    create_collection,
    create_images,
)


def test_bulk_delete_annotations_route__deletes_annotations(
    db_session: Session,
    test_client: TestClient,
) -> None:
    collection = create_collection(session=db_session)
    image = create_images(
        db_session=db_session,
        collection_id=collection.collection_id,
        images=[ImageStub(path="a.png")],
    )[0]
    label = create_annotation_label(
        session=db_session,
        root_collection_id=collection.collection_id,
        label_name="dog",
    )
    annotations = create_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        collection_name="ground_truth",
        annotations=[
            AnnotationDetails(
                sample_id=image.sample_id,
                annotation_label_id=label.annotation_label_id,
            )
        ],
    )
    annotation = annotations[0]
    annotation_id = annotation.sample_id
    annotation_collection_id = annotation.sample.collection_id

    response = test_client.request(
        "DELETE",
        f"/api/collections/{annotation_collection_id}/annotations",
        json={"annotation_ids": [str(annotation_id)]},
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {"deleted_count": 1}
    assert db_session.get(AnnotationBaseTable, annotation_id) is None
    assert db_session.get(SampleTable, annotation_id) is None


def test_bulk_delete_annotations_route__rejects_wrong_collection(
    db_session: Session,
    test_client: TestClient,
) -> None:
    collection = create_collection(session=db_session)
    other_source = create_collection(
        session=db_session,
        parent_collection_id=collection.collection_id,
        sample_type=SampleType.ANNOTATION,
        collection_name="other",
    )
    image = create_images(
        db_session=db_session,
        collection_id=collection.collection_id,
        images=[ImageStub(path="a.png")],
    )[0]
    label = create_annotation_label(
        session=db_session,
        root_collection_id=collection.collection_id,
        label_name="dog",
    )
    annotation = create_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        collection_name="ground_truth",
        annotations=[
            AnnotationDetails(
                sample_id=image.sample_id,
                annotation_label_id=label.annotation_label_id,
            )
        ],
    )[0]

    response = test_client.request(
        "DELETE",
        f"/api/collections/{other_source.collection_id}/annotations",
        json={"annotation_ids": [str(annotation.sample_id)]},
    )

    assert response.status_code == HTTP_STATUS_BAD_REQUEST
    assert db_session.get(AnnotationBaseTable, annotation.sample_id) is not None
