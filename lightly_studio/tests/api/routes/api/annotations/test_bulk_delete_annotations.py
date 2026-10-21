from __future__ import annotations

from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from sqlmodel import Session, select

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_NOT_FOUND,
    HTTP_STATUS_OK,
    HTTP_STATUS_UNPROCESSABLE_ENTITY,
)
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable, AnnotationType
from lightly_studio.models.evaluation_run import EvaluationRunCreate, EvaluationTaskType
from lightly_studio.resolvers import embedding_region_resolver, evaluation_run_resolver
from tests.helpers_resolvers import (
    AnnotationDetails,
    create_annotation_label,
    create_annotations,
    create_collection,
    create_image,
)


def test_bulk_delete_annotations(db_session: Session, test_client: TestClient) -> None:
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    label = create_annotation_label(session=db_session, root_collection_id=collection.collection_id)
    annotations = create_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=image.sample_id,
                annotation_label_id=label.annotation_label_id,
                annotation_type=AnnotationType.OBJECT_DETECTION,
            ),
            AnnotationDetails(
                sample_id=image.sample_id,
                annotation_label_id=label.annotation_label_id,
                annotation_type=AnnotationType.SEGMENTATION_MASK,
                segmentation_mask=[1, 2, 3, 4],
            ),
            AnnotationDetails(
                sample_id=image.sample_id,
                annotation_label_id=label.annotation_label_id,
                annotation_type=AnnotationType.CLASSIFICATION,
            ),
            AnnotationDetails(
                sample_id=image.sample_id,
                annotation_label_id=label.annotation_label_id,
                annotation_type=AnnotationType.OBJECT_DETECTION,
            ),
        ],
        collection_name="ground_truth",
    )
    annotation_collection_id = annotations[0].annotation_collection_id
    annotation_ids = [annotation.sample_id for annotation in annotations]

    response = test_client.post(
        f"/api/collections/{annotation_collection_id}/annotations/bulk_delete",
        json={"annotation_ids": [str(annotation_id) for annotation_id in annotation_ids[:3]]},
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {"deleted_count": 3}
    assert _get_annotation_ids(session=db_session) == {annotation_ids[3]}


def test_bulk_delete_annotations__missing_id(db_session: Session, test_client: TestClient) -> None:
    annotation_collection_id, annotation_ids = _create_annotations(
        session=db_session, annotation_collection_name="ground_truth"
    )

    response = test_client.post(
        f"/api/collections/{annotation_collection_id}/annotations/bulk_delete",
        json={"annotation_ids": [str(annotation_ids[0]), str(uuid4())]},
    )

    assert response.status_code == HTTP_STATUS_NOT_FOUND
    assert _get_annotation_ids(session=db_session) == set(annotation_ids)


def test_bulk_delete_annotations__annotation_of_other_collection(
    db_session: Session, test_client: TestClient
) -> None:
    gt_collection_id, gt_annotation_ids = _create_annotations(
        session=db_session, annotation_collection_name="ground_truth"
    )
    _, pred_annotation_ids = _create_annotations(
        session=db_session, annotation_collection_name="predictions"
    )

    response = test_client.post(
        f"/api/collections/{gt_collection_id}/annotations/bulk_delete",
        json={"annotation_ids": [str(gt_annotation_ids[0]), str(pred_annotation_ids[0])]},
    )

    assert response.status_code == HTTP_STATUS_NOT_FOUND
    assert _get_annotation_ids(session=db_session) == {*gt_annotation_ids, *pred_annotation_ids}


def test_bulk_delete_annotations__empty_ids(db_session: Session, test_client: TestClient) -> None:
    annotation_collection_id, _ = _create_annotations(
        session=db_session, annotation_collection_name="ground_truth"
    )

    response = test_client.post(
        f"/api/collections/{annotation_collection_id}/annotations/bulk_delete",
        json={"annotation_ids": []},
    )

    assert response.status_code == HTTP_STATUS_UNPROCESSABLE_ENTITY


def test_bulk_delete_annotations__marks_evaluation_run_stale(
    db_session: Session, test_client: TestClient
) -> None:
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    label = create_annotation_label(session=db_session, root_collection_id=collection.collection_id)
    annotation_details = [
        AnnotationDetails(sample_id=image.sample_id, annotation_label_id=label.annotation_label_id)
    ]
    gt_annotation = create_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        annotations=annotation_details,
        collection_name="ground_truth",
    )[0]
    pred_annotation = create_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        annotations=annotation_details,
        collection_name="predictions",
    )[0]
    run = evaluation_run_resolver.create(
        session=db_session,
        evaluation_run_input=EvaluationRunCreate(
            name="run",
            gt_annotation_collection_id=gt_annotation.annotation_collection_id,
            pred_annotation_collection_id=pred_annotation.annotation_collection_id,
            dataset_id=collection.dataset_id,
            task_type=EvaluationTaskType.OBJECT_DETECTION,
        ),
    )
    assert run.stale_since is None

    response = test_client.post(
        f"/api/collections/{pred_annotation.annotation_collection_id}/annotations/bulk_delete",
        json={"annotation_ids": [str(pred_annotation.sample_id)]},
    )

    assert response.status_code == HTTP_STATUS_OK
    refreshed = evaluation_run_resolver.get_by_id(session=db_session, evaluation_id=run.id)
    assert refreshed is not None
    assert refreshed.stale_since is not None


def test_bulk_delete_annotations_by_filter(db_session: Session, test_client: TestClient) -> None:
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    cat_label = create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="cat"
    )
    dog_label = create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="dog"
    )
    annotations = create_annotations(
        session=db_session,
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
    annotation_collection_id = annotations[0].annotation_collection_id
    dog_annotation_id = annotations[2].sample_id

    response = test_client.post(
        f"/api/collections/{annotation_collection_id}/annotations/bulk_delete_by_filter",
        json={
            "filter": {
                "filter_type": "annotations",
                "annotation_label_ids": [str(cat_label.annotation_label_id)],
            }
        },
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {"deleted_count": 2}
    assert _get_annotation_ids(session=db_session) == {dog_annotation_id}


def test_bulk_delete_annotations_by_filter__embedding_region(
    db_session: Session, test_client: TestClient, mocker: MockerFixture
) -> None:
    annotation_collection_id, annotation_ids = _create_annotations(
        session=db_session, annotation_collection_name="ground_truth"
    )
    mocker.patch.object(
        embedding_region_resolver,
        "get_sample_ids_in_region",
        return_value=[annotation_ids[1]],
    )

    response = test_client.post(
        f"/api/collections/{annotation_collection_id}/annotations/bulk_delete_by_filter",
        json={
            "filter": {
                "filter_type": "annotations",
                "embedding_region": {
                    "polygon": [{"x": 0, "y": 0}, {"x": 1, "y": 0}, {"x": 1, "y": 1}]
                },
            }
        },
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {"deleted_count": 1}
    assert _get_annotation_ids(session=db_session) == {annotation_ids[0]}


def _create_annotations(
    session: Session, annotation_collection_name: str
) -> tuple[UUID, list[UUID]]:
    """Create two object detections in a new annotation collection.

    Returns:
        The annotation collection ID and the annotation IDs.
    """
    collection = create_collection(session=session)
    image = create_image(session=session, collection_id=collection.collection_id)
    label = create_annotation_label(session=session, root_collection_id=collection.collection_id)
    annotations = create_annotations(
        session=session,
        collection_id=collection.collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=image.sample_id, annotation_label_id=label.annotation_label_id
            ),
            AnnotationDetails(
                sample_id=image.sample_id, annotation_label_id=label.annotation_label_id
            ),
        ],
        collection_name=annotation_collection_name,
    )
    return (
        annotations[0].annotation_collection_id,
        [annotation.sample_id for annotation in annotations],
    )


def _get_annotation_ids(session: Session) -> set[UUID]:
    return set(session.exec(select(AnnotationBaseTable.sample_id)).all())
