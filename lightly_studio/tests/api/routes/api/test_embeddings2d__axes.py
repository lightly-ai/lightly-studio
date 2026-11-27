"""Tests for the embeddings2d endpoint with projection axes."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import pyarrow as pa
import pytest
from fastapi.testclient import TestClient
from pyarrow import ipc
from sqlmodel import Session

from tests import helpers_resolvers
from tests.helpers_resolvers import ImageStub


def test_get_embeddings2d__axes(
    test_client: TestClient,
    db_session: Session,
) -> None:
    collection = helpers_resolvers.create_collection(session=db_session)
    embedding_model = helpers_resolvers.create_embedding_model(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_dimension=3,
        set_as_default=True,
    )
    image_a, image_b = helpers_resolvers.create_samples_with_embeddings(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_id=embedding_model.embedding_model_id,
        images_and_embeddings=[
            (ImageStub(path="a.jpg"), [1.0, 2.0, 3.0]),
            (ImageStub(path="b.jpg"), [4.0, 5.0, 6.0]),
        ],
    )

    response = test_client.post(
        f"/api/collections/{collection.collection_id}/embeddings2d/default",
        json={"filters": {}, "axes": {"x": [1.0, 0.0, 0.0], "y": [0.0, 1.0, 0.0]}},
    )

    assert response.status_code == 200
    table = ipc.open_stream(pa.BufferReader(response.content)).read_all()
    sample_ids = [UUID(sample_id) for sample_id in table.column("sample_id").to_pylist()]
    coordinates = zip(table.column("x").to_pylist(), table.column("y").to_pylist())
    # The axes select the first and the second embedding value.
    assert dict(zip(sample_ids, coordinates)) == {
        image_a.sample_id: (1.0, 2.0),
        image_b.sample_id: (4.0, 5.0),
    }


@pytest.mark.parametrize(
    "axes",
    [
        {"x": [1.0, 0.0, 0.0]},
        {"x": [], "y": [0.0, 1.0, 0.0]},
        {"x": ["NaN", 0.0, 0.0], "y": [0.0, 1.0, 0.0]},
    ],
    ids=["missing_y", "empty_x", "nan_x"],
)
def test_get_embeddings2d__axes__invalid(
    test_client: TestClient,
    db_session: Session,
    axes: dict[str, Any],
) -> None:
    collection = helpers_resolvers.create_collection(session=db_session)

    response = test_client.post(
        f"/api/collections/{collection.collection_id}/embeddings2d/default",
        json={"filters": {}, "axes": axes},
    )

    assert response.status_code == 422
