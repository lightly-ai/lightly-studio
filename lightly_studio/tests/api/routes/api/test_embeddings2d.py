"""Tests for the embeddings2d endpoint."""

from __future__ import annotations

import time
from typing import Any

import numpy as np
import pyarrow as pa
import pytest
from fastapi.testclient import TestClient
from pyarrow import ipc
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.dataset.mobileclip_embedding_generator import EMBEDDING_DIMENSION
from lightly_studio.models.tag import TagCreate
from lightly_studio.resolvers import image_resolver, tag_resolver
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from tests.helpers_resolvers import fill_db_with_samples_and_embeddings


def test_get_embeddings2d__2d(
    test_client: TestClient,
    db_session: Session,
) -> None:
    n_samples = 50

    dataset_id = fill_db_with_samples_and_embeddings(
        test_db=db_session,
        n_samples=n_samples,
        embedding_model_names=["model_a"],
        embedding_dimension=EMBEDDING_DIMENSION,
    )
    image_filter = ImageFilter(sample_filter=SampleFilter(dataset_id=dataset_id))

    response = test_client.post(
        "/api/embeddings2d/default", json={"filters": image_filter.model_dump(mode="json")}
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/vnd.apache.arrow.stream"
    assert response.headers["x-content-type-options"].lower() == "nosniff"

    reader = ipc.open_stream(pa.BufferReader(response.content))
    table = reader.read_all()

    assert table.num_rows == n_samples
    assert table.schema.field("x").type == pa.float32()
    assert table.schema.field("y").type == pa.float32()
    assert table.schema.field("fulfils_filter").type == pa.uint8()
    assert table.schema.field("sample_id").type == pa.string()

    x = table.column("x").to_numpy(zero_copy_only=False)
    y = table.column("y").to_numpy(zero_copy_only=False)

    fulfils_filter = table.column("fulfils_filter").to_numpy(zero_copy_only=False)
    assert x.shape == (n_samples,)
    assert y.shape == (n_samples,)
    assert fulfils_filter.shape == (n_samples,)
    np.testing.assert_array_equal(fulfils_filter, np.ones(n_samples, dtype=np.uint8))

    sample_ids = table.column("sample_id").to_pylist()
    expected_sample_ids = [
        str(sample.sample_id)
        for sample in image_resolver.get_all_by_dataset_id(
            session=db_session,
            dataset_id=dataset_id,
        ).samples
    ]
    assert len(sample_ids) == n_samples
    assert set(sample_ids) == set(expected_sample_ids)


def test_get_embeddings2d__no_dataset_id(
    test_client: TestClient,
) -> None:
    json_body: dict[str, Any] = {"filters": {}}
    response = test_client.post("/api/embeddings2d/default", json=json_body)
    assert response.status_code == 400
    assert response.json() == {"error": "Dataset ID must be provided in filters."}


def test_get_embeddings2d__2d__with_tag_filter(
    test_client: TestClient,
    db_session: Session,
    mocker: MockerFixture,
) -> None:
    n_samples = 5

    dataset_id = fill_db_with_samples_and_embeddings(
        test_db=db_session,
        n_samples=n_samples,
        embedding_model_names=["model_a"],
        embedding_dimension=EMBEDDING_DIMENSION,
    )

    samples = image_resolver.get_all_by_dataset_id(
        session=db_session,
        dataset_id=dataset_id,
    ).samples
    assert len(samples) == n_samples

    tagged_count = 2
    tagged_samples = samples[:tagged_count]

    tag = tag_resolver.create(
        session=db_session,
        tag=TagCreate(dataset_id=dataset_id, name="tagged", kind="sample"),
    )
    for sample in tagged_samples:
        tag_resolver.add_tag_to_sample(session=db_session, tag_id=tag.tag_id, sample=sample.sample)

    image_filter = ImageFilter(
        sample_filter=SampleFilter(
            dataset_id=dataset_id,
            tag_ids=[tag.tag_id],
        )
    )

    spy_sample_resolver = mocker.spy(image_resolver, "get_all_by_dataset_id")

    response = test_client.post(
        "/api/embeddings2d/default",
        json={"filters": image_filter.model_dump(mode="json")},
    )

    assert response.status_code == 200

    table = ipc.open_stream(pa.BufferReader(response.content)).read_all()

    sample_ids_payload = table.column("sample_id").to_pylist()
    assert set(sample_ids_payload) == {str(s.sample_id) for s in samples}

    fulfils_filter = table.column("fulfils_filter").to_numpy(zero_copy_only=False)
    assert fulfils_filter.shape == (n_samples,)
    sample_ids_payload_fulfils_filter = {
        sample_id for sample_id, fulfils in zip(sample_ids_payload, fulfils_filter) if fulfils == 1
    }
    assert sample_ids_payload_fulfils_filter == {str(s.sample_id) for s in tagged_samples}

    assert spy_sample_resolver.call_args is not None
    assert spy_sample_resolver.call_args.kwargs["filters"] == image_filter


"""Benchmark for the /embeddings2d/default endpoint.
Deactivated by default.

Results on a M4 Pro with embedding dimension 512 and NO PCA preprocessing:
Benchmark: n_samples=100, elapsed=1.455s
Benchmark: n_samples=500, elapsed=3.040s
Benchmark: n_samples=1000, elapsed=4.700s
Benchmark: n_samples=2000, elapsed=9.332s

Results on a M4 Pro with embedding dimension 512 and PCA preprocessing to 50 dims:
n_samples=100, elapsed=2.634s
Benchmark: n_samples=100, elapsed=2.634s
Benchmark: n_samples=500, elapsed=4.588s
Benchmark: n_samples=1000, elapsed=9.007s
Benchmark: n_samples=2000, elapsed=14.485s


Thus this is super slow.
"""


@pytest.mark.skip(reason="Benchmark, not a real test. Deactivated by default.")
@pytest.mark.parametrize("n_samples", [100, 500, 1_000, 2_000])
def test_get_embeddings2d_2d_benchmark(
    n_samples: int,
    test_client: TestClient,
    db_session: Session,
) -> None:
    start_time = time.perf_counter()
    fill_db_with_samples_and_embeddings(
        test_db=db_session,
        n_samples=n_samples,
        embedding_model_names=["model_a"],
        embedding_dimension=EMBEDDING_DIMENSION,
    )

    response = test_client.post("/api/embeddings2d/default")
    response.raise_for_status()

    ipc.open_stream(pa.BufferReader(response.content)).read_all()
    elapsed = time.perf_counter() - start_time

    raise ValueError(f"Benchmark: n_samples={n_samples}, elapsed={elapsed:.3f}s")
