"""Evaluation query contracts through the sample filtering API."""

from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from tests.helpers_resolvers import create_collection, create_image
from tests.resolvers.evaluation_sample_metric_resolver.helpers import (
    SampleMetricStub,
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
        for name in ["a", "b", "missing"]
    ]
    run = create_run(session=db_session, collection_id=collection.collection_id, name="run1")
    create_sample_metrics(
        session=db_session,
        run_id=run.id,
        sample_metrics=[
            SampleMetricStub(sample_id=images[0].sample_id, metrics={"fp": 0, "tp": 1}),
            SampleMetricStub(sample_id=images[1].sample_id, metrics={"fp": 2, "tp": 1}),
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
                                "metric_name": "absent",
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
    assert [sample["file_name"] for sample in response.json()["data"]] == ["a.jpg"]
