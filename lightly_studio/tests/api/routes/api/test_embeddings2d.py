"""Tests for the embeddings2d endpoint."""

from __future__ import annotations

import json
import time

import numpy as np
import pyarrow as pa
import pytest
from fastapi.testclient import TestClient
from pyarrow import ipc
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.dataset.mobileclip_embedding_generator import EMBEDDING_DIMENSION
from lightly_studio.models.collection import SampleType
from lightly_studio.models.tag import TagCreate
from lightly_studio.resolvers import (
    image_resolver,
    metadata_resolver,
    sample_resolver,
    tag_resolver,
    video_resolver,
)
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from lightly_studio.resolvers.video_resolver.video_filter import VideoFilter
from tests.helpers_resolvers import (
    create_collection,
    create_embedding_model,
    create_sample_embedding,
    fill_db_with_samples_and_embeddings,
)
from tests.resolvers.video.helpers import VideoStub, create_videos


def test_get_embeddings2d__2d(
    test_client: TestClient,
    db_session: Session,
) -> None:
    n_samples = 50

    collection_id = fill_db_with_samples_and_embeddings(
        session=db_session,
        n_samples=n_samples,
        embedding_model_names=["model_a"],
        embedding_dimension=EMBEDDING_DIMENSION,
    )
    response = test_client.post(
        f"/api/collections/{collection_id}/embeddings2d/default", json={"filters": {}}
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
    assert table.schema.field("color_category").type == pa.uint8()
    assert table.schema.field("sample_id").type == pa.string()

    x = table.column("x").to_numpy(zero_copy_only=False)
    y = table.column("y").to_numpy(zero_copy_only=False)

    fulfils_filter = table.column("fulfils_filter").to_numpy(zero_copy_only=False)
    assert x.shape == (n_samples,)
    assert y.shape == (n_samples,)
    assert fulfils_filter.shape == (n_samples,)
    np.testing.assert_array_equal(fulfils_filter, np.ones(n_samples, dtype=np.uint8))

    color_category = table.column("color_category").to_numpy(zero_copy_only=False)
    np.testing.assert_array_equal(color_category, np.ones(n_samples, dtype=np.uint8))
    assert json.loads(table.schema.metadata[b"color_legend"]) == {}

    sample_ids = table.column("sample_id").to_pylist()
    expected_sample_ids = [
        str(sample.sample_id)
        for sample in image_resolver.get_all_by_collection_id(
            session=db_session,
            collection_id=collection_id,
        ).samples
    ]
    assert len(sample_ids) == n_samples
    assert set(sample_ids) == set(expected_sample_ids)


def test_get_embeddings2d__2d__with_tag_filter(
    test_client: TestClient,
    db_session: Session,
    mocker: MockerFixture,
) -> None:
    n_samples = 5

    collection_id = fill_db_with_samples_and_embeddings(
        session=db_session,
        n_samples=n_samples,
        embedding_model_names=["model_a"],
        embedding_dimension=EMBEDDING_DIMENSION,
    )

    samples = image_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection_id,
    ).samples
    assert len(samples) == n_samples

    tagged_count = 2
    tagged_samples = samples[:tagged_count]

    tag = tag_resolver.create(
        session=db_session,
        tag=TagCreate(collection_id=collection_id, name="tagged", kind="sample"),
    )
    for sample in tagged_samples:
        tag_resolver.add_tag_to_sample(session=db_session, tag_id=tag.tag_id, sample=sample.sample)

    image_filter = ImageFilter(
        sample_filter=SampleFilter(
            tag_ids=[tag.tag_id],
        )
    )

    spy_sample_resolver = mocker.spy(image_resolver, "get_sample_ids")

    response = test_client.post(
        f"/api/collections/{collection_id}/embeddings2d/default",
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

    color_category = table.column("color_category").to_numpy(zero_copy_only=False)
    np.testing.assert_array_equal(color_category, fulfils_filter)

    assert spy_sample_resolver.call_args is not None
    assert spy_sample_resolver.call_args.kwargs["filters"] == image_filter


def test_get_embeddings2d__with_video_filter(
    test_client: TestClient,
    db_session: Session,
    mocker: MockerFixture,
) -> None:
    # Create a video collection
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    collection_id = collection.collection_id

    # Create embedding model
    embedding_model = create_embedding_model(
        session=db_session,
        collection_id=collection_id,
        embedding_model_name="model_a",
        embedding_dimension=EMBEDDING_DIMENSION,
    )

    # Create videos
    video_ids = create_videos(
        session=db_session,
        collection_id=collection_id,
        videos=[VideoStub(path="/videos/video_0.mp4"), VideoStub(path="/videos/video_1.mp4")],
    )
    create_sample_embedding(
        session=db_session,
        sample_id=video_ids[0],
        embedding_model_id=embedding_model.embedding_model_id,
        embedding=[0] * EMBEDDING_DIMENSION,
    )

    create_sample_embedding(
        session=db_session,
        sample_id=video_ids[1],
        embedding_model_id=embedding_model.embedding_model_id,
        embedding=[1] * EMBEDDING_DIMENSION,
    )

    videos = video_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection_id,
    ).samples
    assert len(videos) == 2

    tag = tag_resolver.create(
        session=db_session,
        tag=TagCreate(collection_id=collection_id, name="tagged", kind="sample"),
    )
    tagged_video = videos[0]
    sample_table = sample_resolver.get_by_id(session=db_session, sample_id=tagged_video.sample_id)
    assert sample_table is not None
    tag_resolver.add_tag_to_sample(session=db_session, tag_id=tag.tag_id, sample=sample_table)

    video_filter = VideoFilter(
        sample_filter=SampleFilter(
            tag_ids=[tag.tag_id],
        ),
    )

    spy_video_resolver = mocker.spy(video_resolver, "get_sample_ids")

    response = test_client.post(
        f"/api/collections/{collection_id}/embeddings2d/default",
        json={"filters": video_filter.model_dump(mode="json")},
    )

    assert response.status_code == 200

    table = ipc.open_stream(pa.BufferReader(response.content)).read_all()
    sample_ids_payload = table.column("sample_id").to_pylist()
    fulfils_filter = table.column("fulfils_filter").to_numpy(zero_copy_only=False)

    # All videos should be present in the response
    assert set(sample_ids_payload) == {str(v.sample_id) for v in videos}

    # Only the tagged video should pass the filter
    assert fulfils_filter.shape == (2,)
    filtered_ids = {
        sample_id for sample_id, passes in zip(sample_ids_payload, fulfils_filter) if passes
    }
    assert filtered_ids == {str(tagged_video.sample_id)}

    color_category = table.column("color_category").to_numpy(zero_copy_only=False)
    np.testing.assert_array_equal(color_category, fulfils_filter)

    # Verify the resolver was called with the correct filters
    assert spy_video_resolver.call_args.kwargs["filters"] == video_filter


def test_get_embeddings2d__with_metadata_field_color_by(
    test_client: TestClient,
    db_session: Session,
) -> None:
    n_samples = 3

    collection_id = fill_db_with_samples_and_embeddings(
        session=db_session,
        n_samples=n_samples,
        embedding_model_names=["model_a"],
        embedding_dimension=EMBEDDING_DIMENSION,
    )

    samples = image_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection_id,
    ).samples
    assert len(samples) == n_samples

    cities = ["Paris", "London", "Paris"]
    for sample, city in zip(samples, cities):
        metadata_resolver.set_value_for_sample(
            session=db_session,
            sample_id=sample.sample_id,
            key="city",
            value=city,
        )

    response = test_client.post(
        f"/api/collections/{collection_id}/embeddings2d/default",
        json={
            "filters": {},
            "color_by": {"type": "metadata_field", "key": "city"},
        },
    )

    assert response.status_code == 200

    table = ipc.open_stream(pa.BufferReader(response.content)).read_all()
    sample_ids_payload = table.column("sample_id").to_pylist()
    color_category = table.column("color_category").to_numpy(zero_copy_only=False)

    sample_id_to_color = dict(zip(sample_ids_payload, color_category))
    assert sample_id_to_color[str(samples[0].sample_id)] == 3  # Paris
    assert sample_id_to_color[str(samples[1].sample_id)] == 2  # London
    assert sample_id_to_color[str(samples[2].sample_id)] == 3  # Paris

    legend = json.loads(table.schema.metadata[b"color_legend"])
    assert legend["1"] == "Unassigned"
    assert legend["2"] == "London"
    assert legend["3"] == "Paris"


def test_get_embeddings2d__with_mixed_type_metadata_color_by(
    test_client: TestClient,
    db_session: Session,
) -> None:
    """Mixed-type metadata values for the same key return a 400 error."""
    n_samples = 2

    collection_id = fill_db_with_samples_and_embeddings(
        session=db_session,
        n_samples=n_samples,
        embedding_model_names=["model_a"],
        embedding_dimension=EMBEDDING_DIMENSION,
    )

    samples = image_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection_id,
    ).samples
    assert len(samples) == n_samples

    metadata_resolver.set_value_for_sample(
        session=db_session,
        sample_id=samples[0].sample_id,
        key="score",
        value="high",
    )
    metadata_resolver.set_value_for_sample(
        session=db_session,
        sample_id=samples[1].sample_id,
        key="score",
        value=42,
    )

    response = test_client.post(
        f"/api/collections/{collection_id}/embeddings2d/default",
        json={
            "filters": {},
            "color_by": {"type": "metadata_field", "key": "score"},
        },
    )

    assert response.status_code == 400
    assert "does not match schema type" in response.json()["error"]


def test_get_embeddings2d__with_boolean_metadata_color_by(
    test_client: TestClient,
    db_session: Session,
) -> None:
    n_samples = 3

    collection_id = fill_db_with_samples_and_embeddings(
        session=db_session,
        n_samples=n_samples,
        embedding_model_names=["model_a"],
        embedding_dimension=EMBEDDING_DIMENSION,
    )

    samples = image_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection_id,
    ).samples
    assert len(samples) == n_samples

    # Samples[0] and samples[2] -> False, samples[1] -> True.
    flags = [False, True, False]
    for sample, flag in zip(samples, flags):
        metadata_resolver.set_value_for_sample(
            session=db_session,
            sample_id=sample.sample_id,
            key="is_sunny",
            value=flag,
        )

    response = test_client.post(
        f"/api/collections/{collection_id}/embeddings2d/default",
        json={
            "filters": {},
            "color_by": {"type": "metadata_field", "key": "is_sunny"},
        },
    )

    assert response.status_code == 200

    table = ipc.open_stream(pa.BufferReader(response.content)).read_all()
    sample_ids_payload = table.column("sample_id").to_pylist()
    color_category = table.column("color_category").to_numpy(zero_copy_only=False)

    # False is sorted before True, so False -> cat 2, True -> cat 3.
    sample_id_to_color = dict(zip(sample_ids_payload, color_category))
    assert sample_id_to_color[str(samples[0].sample_id)] == 2  # False -> cat 2
    assert sample_id_to_color[str(samples[1].sample_id)] == 3  # True -> cat 3
    assert sample_id_to_color[str(samples[2].sample_id)] == 2  # False -> cat 2

    legend = json.loads(table.schema.metadata[b"color_legend"])
    assert legend["1"] == "Unassigned"
    assert legend["2"] == "false"
    assert legend["3"] == "true"


def test_get_embeddings2d__with_metadata_field_color_by_and_sample_ids_filter(
    test_client: TestClient,
    db_session: Session,
) -> None:
    n_samples = 4

    collection_id = fill_db_with_samples_and_embeddings(
        session=db_session,
        n_samples=n_samples,
        embedding_model_names=["model_a"],
        embedding_dimension=EMBEDDING_DIMENSION,
    )

    samples = image_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection_id,
    ).samples
    assert len(samples) == n_samples

    cities = ["Paris", "London", "Rome", "Berlin"]
    for sample, city in zip(samples, cities):
        metadata_resolver.set_value_for_sample(
            session=db_session,
            sample_id=sample.sample_id,
            key="city",
            value=city,
        )

    selected_samples = [samples[0], samples[2]]
    selected_sample_ids = [sample.sample_id for sample in selected_samples]

    image_filter = ImageFilter(
        sample_filter=SampleFilter(sample_ids=selected_sample_ids),
    )

    response = test_client.post(
        f"/api/collections/{collection_id}/embeddings2d/default",
        json={
            "filters": image_filter.model_dump(mode="json"),
            "color_by": {"type": "metadata_field", "key": "city"},
        },
    )

    assert response.status_code == 200

    table = ipc.open_stream(pa.BufferReader(response.content)).read_all()
    sample_ids_payload = table.column("sample_id").to_pylist()
    fulfils_filter = table.column("fulfils_filter").to_numpy(zero_copy_only=False)
    color_category = table.column("color_category").to_numpy(zero_copy_only=False)

    assert len(sample_ids_payload) == len(fulfils_filter)
    assert len(sample_ids_payload) == len(color_category)

    sample_id_to_filter = dict(zip(sample_ids_payload, fulfils_filter))

    assert sample_id_to_filter[str(samples[0].sample_id)] == 1
    assert sample_id_to_filter[str(samples[1].sample_id)] == 0
    assert sample_id_to_filter[str(samples[2].sample_id)] == 1
    assert sample_id_to_filter[str(samples[3].sample_id)] == 0

    sample_id_to_color = dict(zip(sample_ids_payload, color_category))
    assert sample_id_to_color[str(samples[0].sample_id)] == 4  # Paris
    assert sample_id_to_color[str(samples[1].sample_id)] == 0  # London, filtered
    assert sample_id_to_color[str(samples[2].sample_id)] == 5  # Rome
    assert sample_id_to_color[str(samples[3].sample_id)] == 0  # Berlin, filtered

    legend = json.loads(table.schema.metadata[b"color_legend"])
    assert legend["1"] == "Unassigned"
    assert legend["2"] == "Berlin"
    assert legend["3"] == "London"
    assert legend["4"] == "Paris"
    assert legend["5"] == "Rome"


def test_get_embeddings2d__with_integer_metadata_color_by__few_values(
    test_client: TestClient,
    db_session: Session,
) -> None:
    """Integer fields with <=50 unique values are treated as direct categories."""
    n_samples = 3

    collection_id = fill_db_with_samples_and_embeddings(
        session=db_session,
        n_samples=n_samples,
        embedding_model_names=["model_a"],
        embedding_dimension=EMBEDDING_DIMENSION,
    )

    samples = image_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection_id,
    ).samples
    assert len(samples) == n_samples

    scores = [1, 2, 1]
    for sample, score in zip(samples, scores):
        metadata_resolver.set_value_for_sample(
            session=db_session,
            sample_id=sample.sample_id,
            key="score",
            value=score,
        )

    response = test_client.post(
        f"/api/collections/{collection_id}/embeddings2d/default",
        json={
            "filters": {},
            "color_by": {"type": "metadata_field", "key": "score"},
        },
    )

    assert response.status_code == 200

    table = ipc.open_stream(pa.BufferReader(response.content)).read_all()
    sample_ids_payload = table.column("sample_id").to_pylist()
    color_category = table.column("color_category").to_numpy(zero_copy_only=False)
    # Unique values [1, 2] are sorted, so 1 -> cat 2, 2 -> cat 3.
    sample_id_to_color = dict(zip(sample_ids_payload, color_category))
    assert sample_id_to_color[str(samples[0].sample_id)] == 2  # score=1 -> cat 2
    assert sample_id_to_color[str(samples[1].sample_id)] == 3  # score=2 -> cat 3
    assert sample_id_to_color[str(samples[2].sample_id)] == 2  # score=1 -> cat 2

    legend = json.loads(table.schema.metadata[b"color_legend"])
    assert legend["1"] == "Unassigned"
    assert legend["2"] == "1"
    assert legend["3"] == "2"


@pytest.mark.parametrize(
    "value",
    [
        {"a": 1},
        [1, 2, 3],
        1.5,
    ],
)
def test_get_embeddings2d__with_unsupported_metadata_color_by(
    value: object,
    test_client: TestClient,
    db_session: Session,
) -> None:
    """Unsupported metadata value types return a 400 error."""
    collection_id = fill_db_with_samples_and_embeddings(
        session=db_session,
        n_samples=1,
        embedding_model_names=["model_a"],
        embedding_dimension=EMBEDDING_DIMENSION,
    )

    samples = image_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection_id,
    ).samples

    metadata_resolver.set_value_for_sample(
        session=db_session,
        sample_id=samples[0].sample_id,
        key="info",
        value=value,
    )

    response = test_client.post(
        f"/api/collections/{collection_id}/embeddings2d/default",
        json={
            "filters": {},
            "color_by": {"type": "metadata_field", "key": "info"},
        },
    )

    assert response.status_code == 400
    assert "unsupported type" in response.json()["error"]


def test_get_embeddings2d__with_integer_metadata_color_by__many_values(
    test_client: TestClient,
    db_session: Session,
) -> None:
    """Integer fields with >50 unique values are grouped into buckets."""
    n_samples = 55

    collection_id = fill_db_with_samples_and_embeddings(
        session=db_session,
        n_samples=n_samples,
        embedding_model_names=["model_a"],
        embedding_dimension=EMBEDDING_DIMENSION,
    )

    samples = image_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection_id,
    ).samples
    assert len(samples) == n_samples

    # Assign 55 distinct integer values (0..54) to exceed the 50-value threshold.
    for i, sample in enumerate(samples):
        metadata_resolver.set_value_for_sample(
            session=db_session,
            sample_id=sample.sample_id,
            key="count",
            value=i,
        )

    response = test_client.post(
        f"/api/collections/{collection_id}/embeddings2d/default",
        json={
            "filters": {},
            "color_by": {"type": "metadata_field", "key": "count"},
        },
    )

    assert response.status_code == 200

    table = ipc.open_stream(pa.BufferReader(response.content)).read_all()
    color_category = table.column("color_category").to_numpy(zero_copy_only=False)

    # All samples must be assigned to a bucket (category >= 2)
    assert all(cat >= 2 for cat in color_category), "All samples should be assigned to a bucket"

    legend = json.loads(table.schema.metadata[b"color_legend"])
    assert legend == {
        "1": "Unassigned",
        "2": "0-2",
        "3": "2-4",
        "4": "4-6",
        "5": "6-8",
        "6": "8-10",
        "7": "10-12",
        "8": "12-14",
        "9": "14-16",
        "10": "16-18",
        "11": "18-20",
        "12": "20-22",
        "13": "22-24",
        "14": "24-26",
        "15": "26-28",
        "16": "28-30",
        "17": "30-32",
        "18": "32-34",
        "19": "34-36",
        "20": "36-38",
        "21": "38-40",
        "22": "40-42",
        "23": "42-44",
        "24": "44-46",
        "25": "46-48",
        "26": "48-50",
        "27": "50-52",
        "28": "52-54",
        "29": "54-56",
    }


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
        session=db_session,
        n_samples=n_samples,
        embedding_model_names=["model_a"],
        embedding_dimension=EMBEDDING_DIMENSION,
    )

    response = test_client.post("/api/embeddings2d/default")
    response.raise_for_status()

    ipc.open_stream(pa.BufferReader(response.content)).read_all()
    elapsed = time.perf_counter() - start_time

    raise ValueError(f"Benchmark: n_samples={n_samples}, elapsed={elapsed:.3f}s")
