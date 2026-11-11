"""Evaluation query contracts through the sample filtering API."""

from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from tests.helpers_resolvers import create_annotation_label, create_collection, create_image
from tests.resolvers.evaluation_sample_metric_resolver.helpers import (
    FalseNegativeMetricStub,
    FalsePositiveMetricStub,
    SampleMetricStub,
    TruePositiveMetricStub,
    create_annotation_metrics,
    create_run,
    create_sample_metrics,
)


@pytest.mark.parametrize(
    ("operator", "expected_names"),
    [
        ("==", ["a.jpg"]),
        ("!=", ["b.jpg"]),
        ("<", []),
        ("<=", ["a.jpg"]),
        (">", ["b.jpg"]),
        (">=", ["a.jpg", "b.jpg"]),
    ],
)
def test_sample_evaluation__list_and_count(
    test_client: TestClient, db_session: Session, operator: str, expected_names: list[str]
) -> None:
    collection = create_collection(session=db_session)
    images = [
        create_image(
            session=db_session, collection_id=collection.collection_id, file_path_abs=f"/{name}.jpg"
        )
        for name in ["a", "b", "missing"]
    ]
    run = create_run(session=db_session, collection_id=collection.collection_id, name="run1")
    create_sample_metrics(
        session=db_session,
        run_id=run.id,
        sample_metrics=[
            SampleMetricStub(sample_id=images[0].sample_id, metrics={"fp": 0}),
            SampleMetricStub(sample_id=images[1].sample_id, metrics={"fp": 2}),
        ],
    )
    expression = {
        "type": "sample_evaluation_match_expr",
        "run_name": "run1",
        "criteria": [
            {
                "type": "evaluation_metric_comparison_expr",
                "metric_name": "fp",
                "operator": operator,
                "value": 0,
            }
        ],
    }
    body: dict[str, Any] = {
        "filters": {"sample_filter": {"query_expr": {"match_expr": expression}}},
        "pagination": {"offset": 0, "limit": 1},
    }
    endpoint = f"/api/collections/{collection.collection_id}/images/list"
    response = test_client.post(endpoint, json=body)
    assert response.status_code == 200
    assert response.json()["total_count"] == len(expected_names)
    body["pagination"]["limit"] = 100
    response = test_client.post(endpoint, json=body)
    assert response.status_code == 200
    assert {sample["file_name"] for sample in response.json()["data"]} == set(expected_names)


def test_sample_evaluation__boolean_criteria(test_client: TestClient, db_session: Session) -> None:
    collection = create_collection(session=db_session)
    images = [
        create_image(
            session=db_session, collection_id=collection.collection_id, file_path_abs=f"/{name}.jpg"
        )
        for name in ["a", "b", "c", "d", "missing"]
    ]
    run = create_run(session=db_session, collection_id=collection.collection_id, name="run1")
    create_sample_metrics(
        session=db_session,
        run_id=run.id,
        sample_metrics=[
            # Each OR branch selects a different sample that also passes NOT.
            SampleMetricStub(sample_id=images[0].sample_id, metrics={"fp": 0, "tp": 1, "fn": 0}),
            SampleMetricStub(sample_id=images[1].sample_id, metrics={"fp": 0, "tp": 0, "fn": 1}),
            # Each AND child excludes a sample that passes the other child.
            SampleMetricStub(sample_id=images[2].sample_id, metrics={"fp": 2, "tp": 1, "fn": 0}),
            SampleMetricStub(sample_id=images[3].sample_id, metrics={"fp": 0, "tp": 0, "fn": 0}),
        ],
    )
    expression = {
        "type": "sample_evaluation_match_expr",
        "run_name": "run1",
        "criteria": [
            {
                "type": "and",
                "children": [
                    {
                        "type": "not",
                        "child": {
                            "type": "evaluation_metric_comparison_expr",
                            "metric_name": "fp",
                            "operator": ">",
                            "value": 0,
                        },
                    },
                    {
                        "type": "or",
                        "children": [
                            {
                                "type": "evaluation_metric_comparison_expr",
                                "metric_name": "tp",
                                "operator": ">=",
                                "value": 1,
                            },
                            {
                                "type": "evaluation_metric_comparison_expr",
                                "metric_name": "fn",
                                "operator": "!=",
                                "value": 0,
                            },
                        ],
                    },
                ],
            }
        ],
    }
    response = test_client.post(
        f"/api/collections/{collection.collection_id}/images/list",
        json={
            "filters": {"sample_filter": {"query_expr": {"match_expr": expression}}},
        },
    )
    assert response.status_code == 200
    assert response.json()["total_count"] == 2
    assert {sample["file_name"] for sample in response.json()["data"]} == {"a.jpg", "b.jpg"}


@pytest.mark.parametrize(
    ("expression", "expected_name"),
    [
        (
            {
                "type": "confusion_match_expr",
                "run_name": "run1",
                "ground_truth": "car",
                "prediction": "truck",
                "criteria": [
                    {
                        "type": "evaluation_metric_comparison_expr",
                        "metric_name": "iou",
                        "operator": ">",
                        "value": 0.5,
                    },
                    {
                        "type": "evaluation_metric_comparison_expr",
                        "metric_name": "score",
                        "operator": ">",
                        "value": 0.5,
                    },
                ],
            },
            "match.jpg",
        ),
        (
            {"type": "false_positive_match_expr", "run_name": "run1", "prediction": "truck"},
            "fp.jpg",
        ),
        (
            {"type": "false_negative_match_expr", "run_name": "run1", "ground_truth": "car"},
            "fn.jpg",
        ),
    ],
)
def test_annotation_evaluation(
    test_client: TestClient, db_session: Session, expression: dict[str, Any], expected_name: str
) -> None:
    collection = create_collection(session=db_session)
    images = [
        create_image(
            session=db_session, collection_id=collection.collection_id, file_path_abs=f"/{name}.jpg"
        )
        for name in ["match", "split", "fp", "fn", "fp_car", "fn_truck"]
    ]
    run = create_run(session=db_session, collection_id=collection.collection_id, name="run1")
    car = create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="car"
    )
    truck = create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="truck"
    )
    create_annotation_metrics(
        session=db_session,
        run_id=run.id,
        pair_metric_stubs=[
            TruePositiveMetricStub(
                sample_id=images[0].sample_id,
                metrics={"iou": 0.8, "score": 0.9},
                gt_annotation_label_id=car.annotation_label_id,
                pred_annotation_label_id=truck.annotation_label_id,
            ),
            TruePositiveMetricStub(
                sample_id=images[1].sample_id,
                metrics={"iou": 0.8, "score": 0.1},
                gt_annotation_label_id=car.annotation_label_id,
                pred_annotation_label_id=truck.annotation_label_id,
            ),
            TruePositiveMetricStub(
                sample_id=images[1].sample_id,
                metrics={"iou": 0.1, "score": 0.9},
                gt_annotation_label_id=car.annotation_label_id,
                pred_annotation_label_id=truck.annotation_label_id,
            ),
            FalsePositiveMetricStub(
                sample_id=images[2].sample_id, pred_annotation_label_id=truck.annotation_label_id
            ),
            FalseNegativeMetricStub(
                sample_id=images[3].sample_id, gt_annotation_label_id=car.annotation_label_id
            ),
            FalsePositiveMetricStub(
                sample_id=images[4].sample_id, pred_annotation_label_id=car.annotation_label_id
            ),
            FalseNegativeMetricStub(
                sample_id=images[5].sample_id, gt_annotation_label_id=truck.annotation_label_id
            ),
        ],
    )
    response = test_client.post(
        f"/api/collections/{collection.collection_id}/images/list",
        json={
            "filters": {"sample_filter": {"query_expr": {"match_expr": expression}}},
        },
    )
    assert response.status_code == 200
    assert response.json()["total_count"] == 1
    assert [sample["file_name"] for sample in response.json()["data"]] == [expected_name]
