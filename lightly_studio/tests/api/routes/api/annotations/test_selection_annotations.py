from __future__ import annotations

from uuid import UUID

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_OK,
    HTTP_STATUS_UNPROCESSABLE_ENTITY,
)
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable, AnnotationType
from lightly_studio.models.evaluation_run import EvaluationRunCreate, EvaluationTaskType
from lightly_studio.resolvers import evaluation_run_resolver
from tests.helpers_resolvers import (
    AnnotationDetails,
    create_annotation_label,
    create_annotations,
    create_collection,
    create_image,
)


def _classification(sample_id: UUID, label_id: UUID) -> AnnotationDetails:
    return AnnotationDetails(
        sample_id=sample_id,
        annotation_label_id=label_id,
        annotation_type=AnnotationType.CLASSIFICATION,
    )


def _annotation_ids(session: Session) -> set[UUID]:
    return set(session.exec(select(AnnotationBaseTable.sample_id)).all())


def test_delete_for_samples__only_selected_images_class_and_source(
    db_session: Session, test_client: TestClient
) -> None:
    collection = create_collection(session=db_session)
    image_a = create_image(session=db_session, collection_id=collection.collection_id)
    image_b = create_image(
        session=db_session, collection_id=collection.collection_id, file_path_abs="/b.jpg"
    )
    image_c = create_image(
        session=db_session, collection_id=collection.collection_id, file_path_abs="/c.jpg"
    )
    raccoon = create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="raccoon"
    )
    label_id = raccoon.annotation_label_id
    gt = create_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        annotations=[
            _classification(image_a.sample_id, label_id),
            _classification(image_b.sample_id, label_id),
        ],
        collection_name="ground_truth",
    )
    model = create_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        annotations=[_classification(image_a.sample_id, label_id)],
        collection_name="model_v1",
    )

    response = test_client.post(
        f"/api/collections/{collection.collection_id}"
        "/annotations/classifications/delete_for_samples",
        json={
            "sample_ids": [str(image_a.sample_id), str(image_c.sample_id)],
            "annotation_label_id": str(label_id),
            "annotation_collection_id": str(gt[0].annotation_collection_id),
        },
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {"deleted_count": 1}
    assert _annotation_ids(db_session) == {gt[1].sample_id, model[0].sample_id}


def test_delete_for_samples__by_filter(db_session: Session, test_client: TestClient) -> None:
    collection = create_collection(session=db_session)
    image_a = create_image(session=db_session, collection_id=collection.collection_id)
    image_b = create_image(
        session=db_session, collection_id=collection.collection_id, file_path_abs="/b.jpg"
    )
    label = create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="raccoon"
    )
    annotations = create_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        annotations=[
            _classification(image_a.sample_id, label.annotation_label_id),
            _classification(image_b.sample_id, label.annotation_label_id),
        ],
        collection_name="ground_truth",
    )

    response = test_client.post(
        f"/api/collections/{collection.collection_id}"
        "/annotations/classifications/delete_for_samples",
        json={
            "filter": {
                "filter_type": "image",
                "sample_filter": {"sample_ids": [str(image_b.sample_id)]},
            },
            "annotation_label_id": str(label.annotation_label_id),
            "annotation_collection_id": str(annotations[0].annotation_collection_id),
        },
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {"deleted_count": 1}
    assert _annotation_ids(db_session) == {annotations[0].sample_id}


def test_delete_for_samples__requires_ids_or_filter(
    db_session: Session, test_client: TestClient
) -> None:
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    label = create_annotation_label(session=db_session, root_collection_id=collection.collection_id)
    annotations = create_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        annotations=[_classification(image.sample_id, label.annotation_label_id)],
        collection_name="ground_truth",
    )

    response = test_client.post(
        f"/api/collections/{collection.collection_id}"
        "/annotations/classifications/delete_for_samples",
        json={
            "annotation_label_id": str(label.annotation_label_id),
            "annotation_collection_id": str(annotations[0].annotation_collection_id),
        },
    )

    assert response.status_code == HTTP_STATUS_UNPROCESSABLE_ENTITY
    assert _annotation_ids(db_session) == {annotations[0].sample_id}


def test_delete_for_samples__marks_evaluation_runs_stale(
    db_session: Session, test_client: TestClient
) -> None:
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    label = create_annotation_label(session=db_session, root_collection_id=collection.collection_id)
    details = [_classification(image.sample_id, label.annotation_label_id)]
    gt_annotation = create_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        annotations=details,
        collection_name="ground_truth",
    )[0]
    pred_annotation = create_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        annotations=details,
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
        f"/api/collections/{collection.collection_id}"
        "/annotations/classifications/delete_for_samples",
        json={
            "sample_ids": [str(image.sample_id)],
            "annotation_label_id": str(label.annotation_label_id),
            "annotation_collection_id": str(pred_annotation.annotation_collection_id),
        },
    )

    assert response.status_code == HTTP_STATUS_OK
    refreshed = evaluation_run_resolver.get_by_id(session=db_session, evaluation_id=run.id)
    assert refreshed is not None
    assert refreshed.stale_since is not None


def test_label_counts__by_annotation_ids(db_session: Session, test_client: TestClient) -> None:
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    deer = create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="deer"
    )
    fox = create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="fox"
    )
    cat = create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="cat"
    )
    annotations = create_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=image.sample_id, annotation_label_id=label.annotation_label_id
            )
            for label in [deer, deer, deer, fox, cat]
        ],
        collection_name="ground_truth",
    )
    selected = [str(annotation.sample_id) for annotation in annotations[:4]]

    response = test_client.post(
        f"/api/collections/{annotations[0].annotation_collection_id}/annotations/label_counts",
        json={"filter": {"filter_type": "annotations", "sample_ids": selected}},
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == [
        {"annotation_label_id": str(deer.annotation_label_id), "label_name": "deer", "count": 3},
        {"annotation_label_id": str(fox.annotation_label_id), "label_name": "fox", "count": 1},
    ]
