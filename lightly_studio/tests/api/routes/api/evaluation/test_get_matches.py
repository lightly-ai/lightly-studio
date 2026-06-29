from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_NOT_FOUND,
    HTTP_STATUS_NOT_IMPLEMENTED,
    HTTP_STATUS_OK,
)
from lightly_studio.models.evaluation_annotation_metric import EvaluationAnnotationMetricCreate
from lightly_studio.models.evaluation_run import EvaluationTaskType
from lightly_studio.resolvers import evaluation_annotation_metric_resolver
from tests.api.routes.api.evaluation import helpers
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
)
from tests.resolvers.evaluation_sample_metric_resolver import (
    helpers as evaluation_sample_metric_helpers,
)


def test_list_evaluation_matches(
    db_session: Session,
    test_client: TestClient,
) -> None:
    dataset = create_collection(session=db_session)
    run = evaluation_sample_metric_helpers.create_run(
        session=db_session,
        dataset_collection_id=dataset.collection_id,
    )
    image = create_image(session=db_session, collection_id=dataset.collection_id)
    label = create_annotation_label(
        session=db_session,
        root_collection_id=dataset.collection_id,
    )
    gt = create_annotation(
        session=db_session,
        collection_id=dataset.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
    )
    pred = create_annotation(
        session=db_session,
        collection_id=dataset.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
    )
    pred_fp = create_annotation(
        session=db_session,
        collection_id=dataset.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
    )
    evaluation_annotation_metric_resolver.create_many(
        session=db_session,
        records=[
            EvaluationAnnotationMetricCreate(
                evaluation_run_id=run.id,
                sample_id=image.sample_id,
                pred_annotation_id=pred.sample_id,
                gt_annotation_id=gt.sample_id,
                metric_name="iou",
                value=0.75,
            ),
            EvaluationAnnotationMetricCreate(
                evaluation_run_id=run.id,
                sample_id=image.sample_id,
                pred_annotation_id=pred_fp.sample_id,
            ),
        ],
    )

    response = test_client.post(
        f"/api/datasets/{dataset.collection_id}/evaluation/runs/{run.id}/matches",
        json={"collection_id": str(dataset.collection_id)},
    )

    assert response.status_code == HTTP_STATUS_OK
    payload = response.json()
    assert payload["total_count"] == 2
    assert [match["match_type"] for match in payload["data"]] == ["tp", "fp"]
    assert payload["data"][0]["iou"] == 0.75
    assert payload["data"][0]["gt_annotation"] is not None
    assert payload["data"][0]["pred_annotation"] is not None
    assert payload["data"][1]["gt_annotation"] is None


def test_list_evaluation_matches__filter_by_match_type(
    db_session: Session,
    test_client: TestClient,
) -> None:
    dataset = create_collection(session=db_session)
    run = evaluation_sample_metric_helpers.create_run(
        session=db_session,
        dataset_collection_id=dataset.collection_id,
    )
    image = create_image(session=db_session, collection_id=dataset.collection_id)
    label = create_annotation_label(
        session=db_session,
        root_collection_id=dataset.collection_id,
    )
    gt = create_annotation(
        session=db_session,
        collection_id=dataset.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
    )
    pred = create_annotation(
        session=db_session,
        collection_id=dataset.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
    )
    gt_fn = create_annotation(
        session=db_session,
        collection_id=dataset.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
    )
    evaluation_annotation_metric_resolver.create_many(
        session=db_session,
        records=[
            EvaluationAnnotationMetricCreate(
                evaluation_run_id=run.id,
                sample_id=image.sample_id,
                pred_annotation_id=pred.sample_id,
                gt_annotation_id=gt.sample_id,
                metric_name="iou",
                value=0.75,
            ),
            EvaluationAnnotationMetricCreate(
                evaluation_run_id=run.id,
                sample_id=image.sample_id,
                gt_annotation_id=gt_fn.sample_id,
            ),
        ],
    )

    response = test_client.post(
        f"/api/datasets/{dataset.collection_id}/evaluation/runs/{run.id}/matches",
        json={"collection_id": str(dataset.collection_id), "match_types": ["fn"]},
    )

    assert response.status_code == HTTP_STATUS_OK
    payload = response.json()
    assert payload["total_count"] == 1
    assert payload["data"][0]["match_type"] == "fn"


def test_list_evaluation_matches__run_not_found(
    test_client: TestClient, mocker: MockerFixture
) -> None:
    dataset_id = uuid4()
    evaluation_run_id = uuid4()
    mocker.patch(
        "lightly_studio.api.routes.api.evaluation.get_matches.evaluation_run_resolver.get_by_id",
        return_value=None,
    )

    response = test_client.post(
        f"/api/datasets/{dataset_id}/evaluation/runs/{evaluation_run_id}/matches",
        json={"collection_id": str(dataset_id)},
    )

    assert response.status_code == HTTP_STATUS_NOT_FOUND


def test_list_evaluation_matches__unsupported_task_type(
    test_client: TestClient, mocker: MockerFixture
) -> None:
    dataset_id = uuid4()
    evaluation_run_id = uuid4()
    mocker.patch(
        "lightly_studio.api.routes.api.evaluation.get_matches.evaluation_run_resolver.get_by_id",
        return_value=helpers.make_evaluation_run(
            run_id=evaluation_run_id,
            name="run_1",
            config_json={},
            created_at=datetime(2026, 5, 18, 10, 0, 0, tzinfo=timezone.utc),
            task_type=EvaluationTaskType.CLASSIFICATION,
        ),
    )
    mock_resolver = mocker.patch(
        "lightly_studio.api.routes.api.evaluation.get_matches.evaluation_annotation_metric_resolver.get_matches_with_payload",
    )

    response = test_client.post(
        f"/api/datasets/{dataset_id}/evaluation/runs/{evaluation_run_id}/matches",
        json={"collection_id": str(dataset_id)},
    )

    assert response.status_code == HTTP_STATUS_NOT_IMPLEMENTED
    mock_resolver.assert_not_called()


def test_list_evaluation_matches__scopes_to_single_sample(
    db_session: Session,
    test_client: TestClient,
) -> None:
    dataset = create_collection(session=db_session)
    run = evaluation_sample_metric_helpers.create_run(
        session=db_session,
        dataset_collection_id=dataset.collection_id,
    )
    image = create_image(session=db_session, collection_id=dataset.collection_id)
    other_image = create_image(
        session=db_session,
        collection_id=dataset.collection_id,
        file_path_abs="/path/to/other.png",
    )
    label = create_annotation_label(
        session=db_session,
        root_collection_id=dataset.collection_id,
    )
    pred_in = create_annotation(
        session=db_session,
        collection_id=dataset.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
    )
    pred_out = create_annotation(
        session=db_session,
        collection_id=dataset.collection_id,
        sample_id=other_image.sample_id,
        annotation_label_id=label.annotation_label_id,
    )
    evaluation_annotation_metric_resolver.create_many(
        session=db_session,
        records=[
            EvaluationAnnotationMetricCreate(
                evaluation_run_id=run.id,
                sample_id=image.sample_id,
                pred_annotation_id=pred_in.sample_id,
            ),
            EvaluationAnnotationMetricCreate(
                evaluation_run_id=run.id,
                sample_id=other_image.sample_id,
                pred_annotation_id=pred_out.sample_id,
            ),
        ],
    )

    response = test_client.post(
        f"/api/datasets/{dataset.collection_id}/evaluation/runs/{run.id}/matches",
        json={
            "collection_id": str(dataset.collection_id),
            "image_filter": {
                "filter_type": "image",
                "sample_filter": {"sample_ids": [str(image.sample_id)]},
            },
        },
    )

    assert response.status_code == HTTP_STATUS_OK
    payload = response.json()
    assert payload["total_count"] == 1
    assert payload["data"][0]["parent_sample_data"]["sample_id"] == str(image.sample_id)
