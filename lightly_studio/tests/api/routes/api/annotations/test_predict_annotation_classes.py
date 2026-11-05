from __future__ import annotations

from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_BAD_REQUEST,
    HTTP_STATUS_NOT_FOUND,
    HTTP_STATUS_OK,
)
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable, AnnotationType
from lightly_studio.services import annotations_service
from lightly_studio.services.annotations_service import AnnotationClassPrediction
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
)


def test_predict_annotation_classes__ok(
    db_session: Session, test_client: TestClient, mocker: MockerFixture
) -> None:
    collection_id, annotation = _create_annotation(
        session=db_session, annotation_type=AnnotationType.OBJECT_DETECTION
    )
    cat_id = UUID(int=1)
    dog_id = UUID(int=2)
    mock_predict = mocker.patch.object(
        annotations_service,
        "predict_annotation_classes",
        return_value=[
            AnnotationClassPrediction(annotation_label_id=dog_id, label_name="dog", score=0.75),
            AnnotationClassPrediction(annotation_label_id=cat_id, label_name="cat", score=0.25),
        ],
    )

    response = test_client.post(
        f"/api/collections/{collection_id}/annotations/{annotation.sample_id}/class_predictions"
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == [
        {"annotation_label_id": str(dog_id), "label_name": "dog", "score": 0.75},
        {"annotation_label_id": str(cat_id), "label_name": "cat", "score": 0.25},
    ]
    mock_predict.assert_called_once()
    assert mock_predict.call_args.kwargs["annotation"].sample_id == annotation.sample_id


def test_predict_annotation_classes__annotation_not_found(
    db_session: Session, test_client: TestClient
) -> None:
    collection = create_collection(session=db_session)

    response = test_client.post(
        f"/api/collections/{collection.collection_id}/annotations/{uuid4()}/class_predictions"
    )

    assert response.status_code == HTTP_STATUS_NOT_FOUND


def test_predict_annotation_classes__not_croppable(
    db_session: Session, test_client: TestClient
) -> None:
    collection_id, annotation = _create_annotation(
        session=db_session, annotation_type=AnnotationType.CLASSIFICATION
    )

    response = test_client.post(
        f"/api/collections/{collection_id}/annotations/{annotation.sample_id}/class_predictions"
    )

    assert response.status_code == HTTP_STATUS_BAD_REQUEST


def _create_annotation(
    session: Session, annotation_type: AnnotationType
) -> tuple[UUID, AnnotationBaseTable]:
    collection = create_collection(session=session)
    label = create_annotation_label(session=session, root_collection_id=collection.collection_id)
    image = create_image(session=session, collection_id=collection.collection_id)
    annotation = create_annotation(
        session=session,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=annotation_type,
    )
    return collection.collection_id, annotation
