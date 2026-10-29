from __future__ import annotations

from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_CONFLICT,
    HTTP_STATUS_NOT_FOUND,
    HTTP_STATUS_OK,
    HTTP_STATUS_UNPROCESSABLE_ENTITY,
)
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.collection import CollectionTable
from lightly_studio.models.evaluation_run import EvaluationRunCreate, EvaluationTaskType
from lightly_studio.resolvers import (
    annotation_resolver,
    collection_resolver,
    evaluation_run_resolver,
)
from tests.helpers_resolvers import (
    AnnotationDetails,
    create_annotation_label,
    create_annotations,
    create_collection,
    create_image,
)


def test_delete_annotation_source(db_session: Session, test_client: TestClient) -> None:
    collection = create_collection(session=db_session)
    annotations = _create_annotations(
        session=db_session, collection=collection, source_name="predictions", count=2
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
    gt_annotation = _create_annotations(
        session=db_session, collection=collection, source_name="ground_truth", count=1
    )[0]
    pred_annotation = _create_annotations(
        session=db_session, collection=collection, source_name="predictions", count=1
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


def test_move_annotations(db_session: Session, test_client: TestClient) -> None:
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    label = create_annotation_label(session=db_session, root_collection_id=collection.collection_id)
    details = AnnotationDetails(
        sample_id=image.sample_id, annotation_label_id=label.annotation_label_id
    )
    annotations = create_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        annotations=[details, details],
        collection_name="predictions",
    )
    annotation_ids = [annotation.sample_id for annotation in annotations]

    response = test_client.post(
        f"/api/collections/{collection.collection_id}/annotations/move_to_source",
        json={
            "annotation_ids": [str(annotation_id) for annotation_id in annotation_ids],
            "target_annotation_collection_name": " ground_truth ",
        },
    )

    assert response.status_code == HTTP_STATUS_OK
    target_id = collection_resolver.get_by_name(
        session=db_session, name="ground_truth", parent_collection_id=collection.collection_id
    )
    assert response.json() == {"annotation_collection_id": str(target_id), "moved_count": 2}
    moved = annotation_resolver.get_by_ids(session=db_session, annotation_ids=annotation_ids)
    assert {annotation.annotation_collection_id for annotation in moved} == {target_id}


def test_move_annotations__empty_ids(db_session: Session, test_client: TestClient) -> None:
    collection = create_collection(session=db_session)

    response = test_client.post(
        f"/api/collections/{collection.collection_id}/annotations/move_to_source",
        json={"annotation_ids": [], "target_annotation_collection_name": "ground_truth"},
    )

    assert response.status_code == HTTP_STATUS_UNPROCESSABLE_ENTITY


def _create_annotations(
    session: Session, collection: CollectionTable, source_name: str, count: int
) -> list[AnnotationBaseTable]:
    """Create count box annotations on a new image in the named annotation source."""
    image = create_image(session=session, collection_id=collection.collection_id)
    label = create_annotation_label(
        session=session, root_collection_id=collection.collection_id, label_name=source_name
    )
    details = AnnotationDetails(
        sample_id=image.sample_id, annotation_label_id=label.annotation_label_id
    )
    return create_annotations(
        session=session,
        collection_id=collection.collection_id,
        annotations=[details] * count,
        collection_name=source_name,
    )
