from __future__ import annotations

from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_BAD_REQUEST,
    HTTP_STATUS_NOT_FOUND,
    HTTP_STATUS_UNPROCESSABLE_ENTITY,
)
from lightly_studio.models.collection import SampleType
from tests.helpers_resolvers import create_collection, create_image


def test_v1_query_samples__pages(test_client: TestClient, db_session: Session) -> None:
    collection_id = create_collection(
        session=db_session, sample_type=SampleType.IMAGE
    ).collection_id
    for path in ["/a.png", "/b.png", "/c.png"]:
        create_image(session=db_session, collection_id=collection_id, file_path_abs=path)
    url = f"/api/v1/collections/{collection_id}/samples:query"
    sort = [{"field": {"table": "image", "name": "file_name"}, "direction": "desc"}]

    first = test_client.post(url, json={"sort": sort, "limit": 2}).json()
    second = test_client.post(
        url, json={"sort": sort, "limit": 2, "cursor": first["next_cursor"]}
    ).json()

    assert [s["file_name"] for s in first["samples"]] == ["c.png", "b.png"]
    assert [s["file_name"] for s in second["samples"]] == ["a.png"]
    assert second["next_cursor"] is None


@pytest.mark.parametrize(
    ("body", "status_code"),
    [
        ({"cursor": "not a cursor"}, HTTP_STATUS_BAD_REQUEST),
        ({"include": ["metadata"]}, HTTP_STATUS_BAD_REQUEST),
        ({"limit": 1001}, HTTP_STATUS_UNPROCESSABLE_ENTITY),
        ({"cursor": "x", "offset": 1}, HTTP_STATUS_UNPROCESSABLE_ENTITY),
    ],
)
def test_v1_query_samples__bad_request(
    test_client: TestClient, db_session: Session, body: dict[str, object], status_code: int
) -> None:
    collection_id = create_collection(
        session=db_session, sample_type=SampleType.IMAGE
    ).collection_id

    response = test_client.post(f"/api/v1/collections/{collection_id}/samples:query", json=body)

    assert response.status_code == status_code


def test_v1_query_samples__video_collection(test_client: TestClient, db_session: Session) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)

    response = test_client.post(
        f"/api/v1/collections/{collection.collection_id}/samples:query", json={}
    )

    assert response.status_code == HTTP_STATUS_BAD_REQUEST


def test_v1_query_samples__not_found(test_client: TestClient) -> None:
    collection_id = UUID("00000000-0000-0000-0000-000000000001")

    response = test_client.post(f"/api/v1/collections/{collection_id}/samples:query", json={})

    assert response.status_code == HTTP_STATUS_NOT_FOUND
