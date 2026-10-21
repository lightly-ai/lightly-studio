"""Metadata query expressions through the image and video filtering APIs."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import metadata_resolver
from tests.helpers_resolvers import create_collection, create_image
from tests.resolvers.video.helpers import VideoStub, create_video


@pytest.mark.parametrize("sample_type", [SampleType.IMAGE, SampleType.VIDEO])
@pytest.mark.parametrize(
    ("path", "operator", "value", "expected_indices"),
    [
        ("score", "==", 2, [1, 2]),
        ("score", "!=", 2.0, [0]),
        ("score", "<", 2, [0]),
        ("score", "<=", 2, [0, 1, 2]),
        ("score", ">", -1, [1, 2]),
        ("score", ">=", 2, [1, 2]),
        ("camera", "==", "front", [0]),
        ("camera", "!=", "front", [1]),
        ("reviewed", "==", True, [0]),
        ("reviewed", "!=", True, [1]),
        ("odometry.acc[1]", "<", 0.2, [0]),
        ("odometry.acc[-1]", ">=", 0.2, [1]),
    ],
)
def test_metadata_query__list_and_count(  # noqa: PLR0913
    test_client: TestClient,
    db_session: Session,
    sample_type: SampleType,
    path: str,
    operator: str,
    value: str | bool | int | float,
    expected_indices: list[int],
) -> None:
    collection = create_collection(session=db_session, sample_type=sample_type)
    metadata_values: list[dict[str, Any]] = [
        {"score": -1.5, "camera": "front", "reviewed": True, "odometry": {"acc": [1, 0.1]}},
        {"score": 2, "camera": "rear", "reviewed": False, "odometry": {"acc": [1, 0.3]}},
        {"score": 2.0},
        {"score": "2", "camera": 1, "reviewed": "true"},
        {"score": True},
        {"score": None, "camera": None, "reviewed": None},
        {"score": [], "camera": {}, "reviewed": []},
        {},
    ]
    sample_ids = []
    for index, metadata in enumerate(metadata_values):
        if sample_type == SampleType.IMAGE:
            sample_id = create_image(
                session=db_session,
                collection_id=collection.collection_id,
                file_path_abs=f"/image{index}.jpg",
            ).sample_id
        else:
            sample_id = create_video(
                session=db_session,
                collection_id=collection.collection_id,
                video=VideoStub(path=f"/video{index}.mp4"),
            ).sample_id
        sample_ids.append(sample_id)
        metadata_resolver.bulk_update_metadata(
            session=db_session, sample_metadata=[(sample_id, metadata)]
        )

    expression = {
        "type": "metadata_comparison_expr",
        "path": path,
        "operator": operator,
        "value": value,
    }
    filters = {"sample_filter": {"query_expr": {"match_expr": expression}}}
    if sample_type == SampleType.IMAGE:
        endpoint = f"/api/collections/{collection.collection_id}/images/list"
        body = {"filters": filters, "pagination": {"offset": 0, "limit": 1}}
    else:
        endpoint = f"/api/collections/{collection.collection_id}/video/"
        body = {"filter": filters}
    # A page of one sample must still report the full filtered count.
    response = test_client.post(endpoint, json=body, params={"offset": 0, "limit": 1})
    assert response.status_code == 200
    assert response.json()["total_count"] == len(expected_indices)
    if sample_type == SampleType.IMAGE:
        body["pagination"] = {"offset": 0, "limit": 100}
    response = test_client.post(endpoint, json=body)
    assert response.status_code == 200
    assert {sample["sample_id"] for sample in response.json()["data"]} == {
        str(sample_ids[index]) for index in expected_indices
    }


@pytest.mark.parametrize(
    ("operator", "expected_names"),
    [
        ("and", ["front.jpg"]),
        ("or", ["front.jpg", "rear.jpg"]),
        ("not", ["rear.jpg", "missing.jpg"]),
    ],
)
def test_metadata_query__boolean_composition(
    test_client: TestClient, db_session: Session, operator: str, expected_names: list[str]
) -> None:
    collection = create_collection(session=db_session)
    for name, metadata, width in [
        ("front.jpg", {"camera": "front"}, 800),
        ("rear.jpg", {"camera": "rear"}, 400),
        ("missing.jpg", {}, 400),
    ]:
        image = create_image(
            session=db_session,
            collection_id=collection.collection_id,
            file_path_abs=f"/{name}",
            width=width,
        )
        metadata_resolver.bulk_update_metadata(
            session=db_session, sample_metadata=[(image.sample_id, metadata)]
        )
    metadata_expr = {
        "type": "metadata_comparison_expr",
        "path": "camera",
        "operator": "==",
        "value": "front",
    }
    width_expr = {
        "type": "integer_expr",
        "field": {"table": "image", "name": "width"},
        "operator": ">=",
        "value": 640,
    }
    expression: dict[str, Any] = (
        {"type": operator, "child": metadata_expr}
        if operator == "not"
        else {"type": operator, "children": [metadata_expr, width_expr]}
    )
    if operator == "or":
        expression["children"][1] = {
            "type": "string_expr",
            "field": {"table": "image", "name": "file_name"},
            "operator": "==",
            "value": "rear.jpg",
        }
    response = test_client.post(
        f"/api/collections/{collection.collection_id}/images/list",
        json={
            "filters": {"sample_filter": {"query_expr": {"match_expr": expression}}},
            "pagination": {"offset": 0, "limit": 100},
        },
    )
    assert response.status_code == 200
    assert {sample["file_name"] for sample in response.json()["data"]} == set(expected_names)
    assert response.json()["total_count"] == len(expected_names)


@pytest.mark.parametrize("value", ["front", True, None, [], {}])
def test_metadata_query__invalid_ordering(
    test_client: TestClient, db_session: Session, value: object
) -> None:
    collection = create_collection(session=db_session)
    response = test_client.post(
        f"/api/collections/{collection.collection_id}/images/list",
        json={
            "filters": {
                "sample_filter": {
                    "query_expr": {
                        "match_expr": {
                            "type": "metadata_comparison_expr",
                            "path": "camera",
                            "operator": ">",
                            "value": value,
                        }
                    }
                }
            }
        },
    )
    assert response.status_code == 422
