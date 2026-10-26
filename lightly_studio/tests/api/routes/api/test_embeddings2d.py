"""Tests for the embeddings2d endpoint."""

from __future__ import annotations

import json
import time
from typing import Any

import numpy as np
import pyarrow as pa
import pytest
from fastapi.testclient import TestClient
from pyarrow import ipc
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.api.routes.api import embeddings2d
from lightly_studio.embed.mobileclip_embedder import EMBEDDING_DIMENSION
from lightly_studio.models.collection import SampleType
from lightly_studio.models.embedding_plot import EmbeddingPlotTable
from lightly_studio.models.recording import RecordingFormat
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.tag import TagCreate
from lightly_studio.resolvers import (
    embedding_plot_resolver,
    image_resolver,
    mcap_group_sequence_resolver,
    recording_resolver,
    sample_resolver,
    tag_resolver,
    twodim_embedding_resolver,
    video_resolver,
)
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.mcap_group_sequence_resolver.mcap_sequence_filter import (
    McapSequenceFilter,
)
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from lightly_studio.resolvers.video_resolver.video_filter import VideoFilter
from tests.helpers_resolvers import (
    create_collection,
    create_embedding_model,
    create_sample_embedding,
    fill_db_with_samples_and_embeddings,
)
from tests.resolvers.video.helpers import VideoStub, create_videos


@pytest.mark.parametrize("count", [0, 2])
@pytest.mark.parametrize(
    "case",
    [
        (SampleType.IMAGE, {}),
        (SampleType.IMAGE, {"sample_filter": {}}),
        (SampleType.VIDEO, {"filter_type": "video", "sample_filter": {}}),
        (SampleType.ANNOTATION, {"filter_type": "annotations"}),
        (SampleType.SEQUENCE, {"filter_type": "mcap_sequence", "sample_filter": {}}),
    ],
)
def test_get_embeddings2d__saved_unfiltered(
    test_client: TestClient,
    db_session: Session,
    mocker: MockerFixture,
    case: tuple[SampleType, dict[str, Any]],
    count: int,
) -> None:
    """Return saved columns, including empty plots, without resolving sample IDs."""
    sample_type, filters = case
    collection = create_collection(session=db_session, sample_type=sample_type)
    model = create_embedding_model(
        session=db_session, collection_id=collection.collection_id, set_as_default=True
    )
    samples = [SampleTable(collection_id=collection.collection_id) for _ in range(count)]
    db_session.add_all(samples)
    db_session.commit()
    ids = [sample.sample_id for sample in samples]
    db_session.add(
        EmbeddingPlotTable(
            collection_id=collection.collection_id,
            embedding_model_id=model.embedding_model_id,
            is_dirty=False,
            data=embedding_plot_resolver.encode(x=[0.5] * count, y=[-0.5] * count, sample_ids=ids),
        )
    )
    db_session.commit()
    mocker.patch.object(
        embeddings2d, "_get_matching_sample_ids", side_effect=AssertionError("Sample lookup")
    )
    mocker.patch.object(
        twodim_embedding_resolver,
        "get_twodim_embeddings",
        side_effect=AssertionError("UUID conversion"),
    )
    response = test_client.post(
        f"/api/collections/{collection.collection_id}/embeddings2d/default",
        json={"filters": filters},
    )
    assert response.status_code == 200
    table = ipc.open_stream(response.content).read_all()
    assert table.to_pydict() == {
        "x": [0.5] * count,
        "y": [-0.5] * count,
        "sample_id": [str(sample_id) for sample_id in ids],
        "fulfils_filter": [1] * count,
        "color_categories": [[]] * count,
    }
    assert table.column_names == ["x", "y", "fulfils_filter", "color_categories", "sample_id"]
    assert table.schema.metadata == {b"color_legend": b"{}"}


@pytest.mark.parametrize(
    "case",
    [
        ({"sample_filter": {"has_captions": False}}, [1, 1]),
        ({"sample_filter": {"region_sample_ids": []}}, [0, 0]),
        ({"sample_filter": {"annotations_filter": {}}}, [0, 0]),
        ({"width": {"min": 0}}, [1, 1]),
    ],
)
def test_get_embeddings2d__active_filter(
    test_client: TestClient,
    db_session: Session,
    mocker: MockerFixture,
    case: tuple[dict[str, Any], list[int]],
) -> None:
    """False, zero and an empty region must still go through filtering."""
    filters, expected = case
    collection_id = fill_db_with_samples_and_embeddings(
        session=db_session, n_samples=2, embedding_model_names=["model"], embedding_dimension=3
    )
    lookup = mocker.spy(embeddings2d, "_get_matching_sample_ids")
    response = test_client.post(
        f"/api/collections/{collection_id}/embeddings2d/default", json={"filters": filters}
    )
    assert response.status_code == 200
    lookup.assert_called_once()
    assert ipc.open_stream(response.content).read_all()["fulfils_filter"].to_pylist() == expected


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
    assert table.schema.field("color_categories").type == pa.list_(pa.uint8())
    assert table.schema.field("sample_id").type == pa.string()

    x = table.column("x").to_numpy(zero_copy_only=False)
    y = table.column("y").to_numpy(zero_copy_only=False)

    fulfils_filter = table.column("fulfils_filter").to_numpy(zero_copy_only=False)
    assert x.shape == (n_samples,)
    assert y.shape == (n_samples,)
    assert fulfils_filter.shape == (n_samples,)
    np.testing.assert_array_equal(fulfils_filter, np.ones(n_samples, dtype=np.uint8))

    # Without `color_by`, every sample has an empty list of color categories.
    color_categories = table.column("color_categories").to_pylist()
    assert color_categories == [[]] * n_samples
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
        tag=TagCreate(collection_id=collection_id, name="tagged"),
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

    # Without `color_by`, color categories are empty regardless of filter state.
    color_categories = table.column("color_categories").to_pylist()
    assert color_categories == [[]] * n_samples

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
        set_as_default=True,
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
        tag=TagCreate(collection_id=collection_id, name="tagged"),
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

    # Without `color_by`, color categories are empty regardless of filter state.
    color_categories = table.column("color_categories").to_pylist()
    assert color_categories == [[]] * len(sample_ids_payload)

    # Verify the resolver was called with the correct filters
    assert spy_video_resolver.call_args.kwargs["filters"] == video_filter


def test_get_embeddings2d__with_mcap_sequence_filter(
    test_client: TestClient,
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.SEQUENCE)
    collection_id = collection.collection_id
    embedding_model = create_embedding_model(
        session=db_session,
        collection_id=collection_id,
        embedding_model_name="model_a",
        embedding_dimension=EMBEDDING_DIMENSION,
        set_as_default=True,
    )
    recording_id = recording_resolver.create(
        session=db_session,
        dataset_id=collection.dataset_id,
        uri="/bags/drive_001.mcap",
        format_=RecordingFormat.MCAP,
    )
    sequence_ids = []
    for value in (0, 1):
        sequence_id = mcap_group_sequence_resolver.create(
            session=db_session, collection_id=collection_id, recording_id=recording_id
        )
        create_sample_embedding(
            session=db_session,
            sample_id=sequence_id,
            embedding_model_id=embedding_model.embedding_model_id,
            embedding=[value] * EMBEDDING_DIMENSION,
        )
        sequence_ids.append(sequence_id)
    tag = tag_resolver.create(
        session=db_session,
        tag=TagCreate(collection_id=collection_id, name="tagged"),
    )
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session, tag_id=tag.tag_id, sample_ids=[sequence_ids[0]]
    )
    sequence_filter = McapSequenceFilter(sample_filter=SampleFilter(tag_ids=[tag.tag_id]))

    response = test_client.post(
        f"/api/collections/{collection_id}/embeddings2d/default",
        json={"filters": sequence_filter.model_dump(mode="json")},
    )

    assert response.status_code == 200
    table = ipc.open_stream(pa.BufferReader(response.content)).read_all()
    sample_ids_payload = table.column("sample_id").to_pylist()
    fulfils_filter = table.column("fulfils_filter").to_numpy(zero_copy_only=False)
    # Both sequences are in the plot, and only the tagged sequence passes the filter.
    assert set(sample_ids_payload) == {str(sequence_id) for sequence_id in sequence_ids}
    filtered_ids = {
        sample_id for sample_id, passes in zip(sample_ids_payload, fulfils_filter) if passes
    }
    assert filtered_ids == {str(sequence_ids[0])}


def test_get_embeddings2d__rejects_mismatched_filter_type(
    test_client: TestClient,
    db_session: Session,
) -> None:
    """Posting an annotation filter to an image collection returns 400."""
    collection_id = fill_db_with_samples_and_embeddings(
        session=db_session,
        n_samples=3,
        embedding_model_names=["model_a"],
        embedding_dimension=EMBEDDING_DIMENSION,
    )

    response = test_client.post(
        f"/api/collections/{collection_id}/embeddings2d/default",
        json={"filters": {"filter_type": "annotations"}},
    )

    assert response.status_code == 400
    assert "Invalid filter type" in response.json()["detail"]


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
