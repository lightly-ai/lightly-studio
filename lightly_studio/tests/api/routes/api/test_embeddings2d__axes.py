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

IMAGE_EMBEDDINGS = [
    [2.0, 0.0, 0.0],
    [-2.0, 0.0, 0.0],
    [0.0, 1.0, 0.0],
    [0.0, -1.0, 0.0],
]


def test_get_embeddings2d__axes(
    test_client: TestClient,
    db_session: Session,
) -> None:
    collection_id, embedding_by_sample_id = _create_samples(session=db_session)

    response = test_client.post(
        f"/api/collections/{collection_id}/embeddings2d/default",
        json={"filters": {}, "axes": {"x": [2.0, 0.0, 0.0], "y": [0.0, 2.0, 0.0]}},
    )

    assert response.status_code == 200
    table = ipc.open_stream(pa.BufferReader(response.content)).read_all()
    sample_ids = [UUID(sample_id) for sample_id in table.column("sample_id").to_pylist()]
    x_values = table.column("x").to_numpy(zero_copy_only=False)
    y_values = table.column("y").to_numpy(zero_copy_only=False)
    assert len(sample_ids) == 4
    for sample_id, x, y in zip(sample_ids, x_values, y_values):
        embedding = embedding_by_sample_id[sample_id]
        assert x == pytest.approx(2.0 * embedding[0])
        assert y == pytest.approx(2.0 * embedding[1])


@pytest.mark.parametrize(
    "axes",
    [
        {"x": [1.0, 0.0, 0.0]},
        {"x": [], "y": [0.0, 1.0, 0.0]},
    ],
)
def test_get_embeddings2d__axes__invalid(
    test_client: TestClient,
    db_session: Session,
    axes: dict[str, Any],
) -> None:
    collection_id, _ = _create_samples(session=db_session)

    response = test_client.post(
        f"/api/collections/{collection_id}/embeddings2d/default",
        json={"filters": {}, "axes": axes},
    )

    assert response.status_code == 422


@pytest.mark.parametrize("axis", ["x", "y"])
@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity"])
def test_get_embeddings2d__axes__non_finite(
    test_client: TestClient,
    db_session: Session,
    axis: str,
    value: str,
) -> None:
    collection_id, _ = _create_samples(session=db_session)
    axes: dict[str, list[float | str]] = {"x": [1.0, 0.0, 0.0], "y": [0.0, 1.0, 0.0]}
    axes[axis][0] = value

    response = test_client.post(
        f"/api/collections/{collection_id}/embeddings2d/default",
        json={"filters": {}, "axes": axes},
    )

    assert response.status_code == 422
    error = response.json()["detail"][0]
    assert error["type"] == "finite_number"
    assert error["loc"] == ["body", "axes", axis, 0]


def test_get_embeddings2d__axes__dimension_mismatch(
    test_client: TestClient,
    db_session: Session,
) -> None:
    collection_id, _ = _create_samples(session=db_session)

    response = test_client.post(
        f"/api/collections/{collection_id}/embeddings2d/default",
        json={"filters": {}, "axes": {"x": [1.0, 0.0], "y": [0.0, 1.0]}},
    )

    assert response.status_code == 400


def _create_samples(session: Session) -> tuple[UUID, dict[UUID, list[float]]]:
    collection = helpers_resolvers.create_collection(session=session)
    embedding_model = helpers_resolvers.create_embedding_model(
        session=session,
        collection_id=collection.collection_id,
        embedding_dimension=3,
        set_as_default=True,
    )
    images = helpers_resolvers.create_samples_with_embeddings(
        session=session,
        collection_id=collection.collection_id,
        embedding_model_id=embedding_model.embedding_model_id,
        images_and_embeddings=[
            (ImageStub(path=f"sample_{i}.jpg"), embedding)
            for i, embedding in enumerate(IMAGE_EMBEDDINGS)
        ],
    )
    embedding_by_sample_id = {
        image.sample_id: embedding for image, embedding in zip(images, IMAGE_EMBEDDINGS)
    }
    return collection.collection_id, embedding_by_sample_id
