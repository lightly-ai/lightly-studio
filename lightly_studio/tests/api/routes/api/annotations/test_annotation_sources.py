from __future__ import annotations

from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_CONFLICT,
    HTTP_STATUS_NOT_FOUND,
    HTTP_STATUS_OK,
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
    create_caption,
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


def test_delete_annotation_source__has_child_collection(
    db_session: Session, test_client: TestClient
) -> None:
    collection = create_collection(session=db_session)
    pred = _create_annotations(
        session=db_session, collection=collection, source_name="predictions", count=1
    )[0]
    create_caption(
        session=db_session,
        collection_id=pred.annotation_collection_id,
        parent_sample_id=pred.sample_id,
    )

    response = test_client.delete(
        f"/api/collections/{collection.collection_id}/annotation_collections/"
        f"{pred.annotation_collection_id}"
    )

    assert response.status_code == HTTP_STATUS_CONFLICT
    assert annotation_resolver.get_by_id(session=db_session, annotation_id=pred.sample_id)


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
