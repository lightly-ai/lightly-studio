from __future__ import annotations

from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_CONFLICT,
    HTTP_STATUS_NOT_FOUND,
    HTTP_STATUS_OK,
)
from lightly_studio.models.collection import SampleType
from lightly_studio.models.evaluation_run import EvaluationRunCreate, EvaluationTaskType
from lightly_studio.resolvers import (
    annotation_resolver,
    collection_resolver,
    evaluation_run_resolver,
)
from tests.helpers_resolvers import (
    create_collection,
    create_image,
    create_source_annotations,
)


def test_delete_annotation_source(db_session: Session, test_client: TestClient) -> None:
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    annotations = create_source_annotations(
        session=db_session, image=image, source_name="predictions", count=2
    )
    source_id = annotations[0].annotation_collection_id

    response = test_client.delete(
        f"/api/collections/{collection.collection_id}/annotation_collections/{source_id}"
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {"deleted_annotation_count": 2}
    assert collection_resolver.get_by_id(session=db_session, collection_id=source_id) is None


def test_delete_annotation_source__not_found(db_session: Session, test_client: TestClient) -> None:
    collection = create_collection(session=db_session)

    response = test_client.delete(
        f"/api/collections/{collection.collection_id}/annotation_collections/"
        f"{collection.collection_id}"
    )

    assert response.status_code == HTTP_STATUS_NOT_FOUND


def test_delete_annotation_source__used_by_evaluation_run(
    db_session: Session, test_client: TestClient
) -> None:
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    gt_annotation = create_source_annotations(
        session=db_session, image=image, source_name="ground_truth", count=1
    )[0]
    pred_annotation = create_source_annotations(
        session=db_session, image=image, source_name="predictions", count=1
    )[0]
    evaluation_run_resolver.create(
        session=db_session,
        evaluation_run_input=EvaluationRunCreate(
            name="run_a",
            gt_annotation_collection_id=gt_annotation.annotation_collection_id,
            pred_annotation_collection_id=pred_annotation.annotation_collection_id,
            dataset_id=collection.dataset_id,
            task_type=EvaluationTaskType.OBJECT_DETECTION,
        ),
    )

    response = test_client.delete(
        f"/api/collections/{collection.collection_id}/annotation_collections/"
        f"{gt_annotation.annotation_collection_id}"
    )

    assert response.status_code == HTTP_STATUS_CONFLICT
    assert response.json() == {
        "error": "The annotation source 'ground_truth' is used by the evaluation runs run_a. "
        "Delete these evaluation runs first."
    }


def test_delete_annotation_source__has_child_collection(
    db_session: Session, test_client: TestClient
) -> None:
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    pred = create_source_annotations(
        session=db_session, image=image, source_name="predictions", count=1
    )[0]
    create_collection(
        session=db_session,
        collection_name="crops",
        parent_collection_id=pred.annotation_collection_id,
        sample_type=SampleType.IMAGE,
    )

    response = test_client.delete(
        f"/api/collections/{collection.collection_id}/annotation_collections/"
        f"{pred.annotation_collection_id}"
    )

    assert response.status_code == HTTP_STATUS_CONFLICT
    assert annotation_resolver.get_by_id(session=db_session, annotation_id=pred.sample_id)
