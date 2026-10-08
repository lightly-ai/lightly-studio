"""Tests for projection axes in region-based tagging requests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.api.routes.api.status import HTTP_STATUS_UNPROCESSABLE_ENTITY
from tests import helpers_resolvers


@pytest.mark.parametrize("axis", ["x", "y"])
@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity"])
def test_add_samples_by_filter__embedding_region__non_finite_axes(
    db_session: Session,
    test_client: TestClient,
    axis: str,
    value: str,
) -> None:
    collection = helpers_resolvers.create_collection(session=db_session)
    collection_id = collection.collection_id
    tag = helpers_resolvers.create_tag(
        session=db_session, collection_id=collection_id, kind="sample"
    )
    axes: dict[str, list[float | str]] = {"x": [1.0, 0.0, 0.0], "y": [0.0, 1.0, 0.0]}
    axes[axis][0] = value

    response = test_client.post(
        f"/api/collections/{collection_id}/tags/{tag.tag_id}/add/samples_by_filter",
        json={
            "filter": {
                "filter_type": "image",
                "sample_filter": {
                    "embedding_region": {
                        "polygon": [
                            {"x": 0.0, "y": 0.0},
                            {"x": 1.0, "y": 0.0},
                            {"x": 0.0, "y": 1.0},
                        ],
                        "axes": axes,
                    }
                },
            }
        },
    )

    assert response.status_code == HTTP_STATUS_UNPROCESSABLE_ENTITY
    error = response.json()["detail"][0]
    assert error["type"] == "finite_number"
    assert error["loc"][-4:] == ["embedding_region", "axes", axis, 0]
