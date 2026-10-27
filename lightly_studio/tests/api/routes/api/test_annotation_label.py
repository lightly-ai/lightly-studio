from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_CONFLICT,
    HTTP_STATUS_CREATED,
    HTTP_STATUS_NOT_FOUND,
    HTTP_STATUS_OK,
)
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.evaluation_run import EvaluationRunCreate, EvaluationTaskType
from lightly_studio.resolvers import annotation_label_resolver, evaluation_run_resolver
from tests.helpers_resolvers import (
    AnnotationDetails,
    create_annotation,
    create_annotation_label,
    create_annotations,
    create_collection,
    create_image,
)


def test_create_annotation_label(db_session: Session, test_client: TestClient) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id
    dataset_id = collection.dataset_id
    input_label = {"annotation_label_name": "cat"}

    result = test_client.post(
        f"/api/collections/{collection_id!s}/annotation_labels",
        json=input_label,
    )
    assert result.status_code == HTTP_STATUS_CREATED
    assert result.json()["annotation_label_id"] is not None

    # Check that the label was created in the database
    all_labels = annotation_label_resolver.get_all(session=db_session, dataset_id=dataset_id)
    assert len(all_labels) == 1
    assert all_labels[0].annotation_label_name == "cat"


def test_get_annotation_labels(db_session: Session, test_client: TestClient) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id
    create_annotation_label(session=db_session, root_collection_id=collection_id, label_name="cat")

    labels_result = test_client.get(f"/api/collections/{collection_id!s}/annotation_labels")
    assert labels_result.status_code == HTTP_STATUS_OK

    assert len(labels_result.json()) == 1
    label = labels_result.json()[0]
    assert label["annotation_label_name"] == "cat"


def test_get_annotation_label(db_session: Session, test_client: TestClient) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id
    label_id = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="cat"
    ).annotation_label_id

    label_result = test_client.get(f"/api/annotation_labels/{label_id!s}")
    assert label_result.status_code == HTTP_STATUS_OK

    label = label_result.json()
    assert label["annotation_label_name"] == "cat"


def test_update_annotation_label(db_session: Session, test_client: TestClient) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id
    dataset_id = collection.dataset_id
    label_id = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="cat"
    ).annotation_label_id

    updated_label = {
        "annotation_label_name": "dog",
        "dataset_id": str(dataset_id),
    }

    label_result = test_client.put(
        f"/api/annotation_labels/{label_id!s}",
        json=updated_label,
    )
    assert label_result.status_code == HTTP_STATUS_OK

    label = label_result.json()
    assert label["annotation_label_name"] == "dog"


def test_update_annotation_label__duplicate_name(
    db_session: Session, test_client: TestClient
) -> None:
    collection = create_collection(session=db_session)
    create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="cat"
    )
    dog_id = create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="dog"
    ).annotation_label_id

    result = test_client.put(
        f"/api/annotation_labels/{dog_id!s}",
        json={"annotation_label_name": "cat", "dataset_id": str(collection.dataset_id)},
    )

    assert result.status_code == HTTP_STATUS_CONFLICT
    # The test client shares the session, which the failed update left in a failed state.
    db_session.rollback()


def test_read_annotation_labels_with_counts(db_session: Session, test_client: TestClient) -> None:
    collection_id = create_collection(session=db_session).collection_id
    image_id = create_image(session=db_session, collection_id=collection_id).sample_id
    cat_id = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="cat"
    ).annotation_label_id
    create_annotation_label(session=db_session, root_collection_id=collection_id, label_name="dog")
    create_annotation(
        session=db_session,
        collection_id=collection_id,
        sample_id=image_id,
        annotation_label_id=cat_id,
    )

    result = test_client.get(f"/api/collections/{collection_id!s}/annotation_labels_with_counts")

    assert result.status_code == HTTP_STATUS_OK
    counts = {row["annotation_label_name"]: row["annotation_count"] for row in result.json()}
    assert counts == {"cat": 1, "dog": 0}


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


def test_delete_annotation_label__deletes_its_annotations(
    db_session: Session, test_client: TestClient
) -> None:
    collection_id = create_collection(session=db_session).collection_id
    image_id = create_image(session=db_session, collection_id=collection_id).sample_id
    cat_id = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="cat"
    ).annotation_label_id
    dog_id = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="dog"
    ).annotation_label_id
    for label_id in (cat_id, cat_id, dog_id):
        create_annotation(
            session=db_session,
            collection_id=collection_id,
            sample_id=image_id,
            annotation_label_id=label_id,
        )

    result = test_client.delete(f"/api/annotation_labels/{cat_id!s}")
    assert result.status_code == HTTP_STATUS_OK

    remaining_label_ids = db_session.exec(select(AnnotationBaseTable.annotation_label_id)).all()
    assert remaining_label_ids == [dog_id]


def test_delete_annotation_label__marks_evaluation_runs_stale(
    db_session: Session, test_client: TestClient
) -> None:
    runs = []
    label_id = None
    for index in range(2):
        collection = create_collection(session=db_session, collection_name=f"collection_{index}")
        image = create_image(session=db_session, collection_id=collection.collection_id)
        if label_id is None:
            label_id = create_annotation_label(
                session=db_session,
                root_collection_id=collection.collection_id,
                label_name="cat",
            ).annotation_label_id
        annotation_details = [
            AnnotationDetails(sample_id=image.sample_id, annotation_label_id=label_id)
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
        runs.append(
            evaluation_run_resolver.create(
                session=db_session,
                evaluation_run_input=EvaluationRunCreate(
                    name=f"run_{index}",
                    gt_annotation_collection_id=gt_annotation.annotation_collection_id,
                    pred_annotation_collection_id=pred_annotation.annotation_collection_id,
                    dataset_id=collection.dataset_id,
                    task_type=EvaluationTaskType.OBJECT_DETECTION,
                ),
            )
        )
    assert all(run.stale_since is None for run in runs)

    result = test_client.delete(f"/api/annotation_labels/{label_id!s}")
    assert result.status_code == HTTP_STATUS_OK

    for run in runs:
        refreshed = evaluation_run_resolver.get_by_id(session=db_session, evaluation_id=run.id)
        assert refreshed is not None
        assert refreshed.stale_since is not None
    assert db_session.exec(select(AnnotationBaseTable.sample_id)).all() == []


def test_delete_annotation_label__not_found(test_client: TestClient) -> None:
    result = test_client.delete(f"/api/annotation_labels/{uuid4()!s}")

    assert result.status_code == HTTP_STATUS_NOT_FOUND
