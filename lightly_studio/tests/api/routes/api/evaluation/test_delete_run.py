"""Test deleting evaluations without deleting annotations or other runs."""

from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from sqlmodel import Session, select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.resolvers import (
    evaluation_annotation_metric_resolver,
    evaluation_sample_metric_resolver,
)
from tests.api.routes.api.evaluation import helpers


@pytest.mark.parametrize(
    ("target", "status"),
    [("run", 204), ("missing", 404), ("wrong_dataset", 404), ("invalid", 422), ("retry", 204)],
)
def test_delete_run(
    test_client: TestClient, db_session: Session, mocker: MockerFixture, target: str, status: int
) -> None:
    root = helpers.create_dataset_with_annotations(
        db_session=db_session, annotation_data={"x": 50, "y": 50, "width": 20, "height": 20}
    )
    url = f"/api/datasets/{root.dataset_id}/evaluation/runs"
    run_ids = []
    for name in ("delete", "keep"):
        response = test_client.post(
            url,
            json={
                "name": name,
                "collection_id": str(root.collection_id),
                "task_type": "object_detection",
                "gt_annotation_source": "gt",
                "pred_annotation_source": "pred",
            },
        )
        assert response.status_code == 201
        run_ids.append(UUID(response.json()["evaluation_run_id"]))
    before = test_client.get(url).json()
    annotations = list(db_session.exec(select(AnnotationBaseTable)).all())
    annotation_metrics = [
        evaluation_annotation_metric_resolver.get_all_by_evaluation_run_id(
            session=db_session, evaluation_run_id=run_id
        )
        for run_id in run_ids
    ]
    sample_metrics = [
        evaluation_sample_metric_resolver.get_all_by_evaluation_run_id(
            session=db_session, evaluation_run_id=run_id
        )
        for run_id in run_ids
    ]
    assert all(annotation_metrics)
    assert all(sample_metrics)
    assert annotations
    dataset_id = uuid4() if target == "wrong_dataset" else root.dataset_id
    run_id = str(uuid4()) if target == "missing" else str(run_ids[0])
    if target == "invalid":
        run_id = "invalid"
    target_url = f"/api/datasets/{dataset_id}/evaluation/runs/{run_id}"
    if target == "retry":
        interrupted = mocker.patch.object(
            db_session, "delete", side_effect=RuntimeError("Deletion interrupted")
        )
        with pytest.raises(RuntimeError, match="Deletion interrupted"):
            test_client.delete(target_url)
        mocker.stop(interrupted)
        db_session.rollback()
        assert test_client.get(url).json() == before
    response = test_client.delete(target_url)
    assert response.status_code == status
    expected = [run for run in before if run["id"] != str(run_ids[0])] if status == 204 else before
    assert test_client.get(url).json() == expected
    assert list(db_session.exec(select(AnnotationBaseTable)).all()) == annotations
    for index, saved_id in enumerate(run_ids):
        deleted = status == 204 and index == 0
        assert evaluation_annotation_metric_resolver.get_all_by_evaluation_run_id(
            session=db_session, evaluation_run_id=saved_id
        ) == ([] if deleted else annotation_metrics[index])
        assert evaluation_sample_metric_resolver.get_all_by_evaluation_run_id(
            session=db_session, evaluation_run_id=saved_id
        ) == ([] if deleted else sample_metrics[index])
    if status == 204:
        assert response.content == b""
        assert test_client.delete(f"{url}/{run_id}").status_code == 404
