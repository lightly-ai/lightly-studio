from __future__ import annotations

from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from lightly_studio.analytics import ingest_tracking, tracking
from lightly_studio.analytics.ingest_tracking import (
    IngestFormat,
    IngestSource,
    IngestSourceKind,
)
from lightly_studio.models.collection import SampleType


@pytest.mark.parametrize(
    ("path", "protocol"),
    [
        ("s3://bucket/images", "s3"),
        ("gs://bucket/images", "gs"),
        ("gcs://bucket/images", "gcs"),
        ("az://container/images", "az"),
        ("hf://datasets/acme/traffic_cams", "hf"),
        ("https://example.com/images", "https"),
    ],
)
def test_get_source__remote(path: str, protocol: str) -> None:
    assert ingest_tracking.get_source(path=path) == IngestSource(
        kind=IngestSourceKind.REMOTE, protocol=protocol
    )


def test_get_source__remote_example_folder() -> None:
    # Remote wins: the example folder name only marks the local download.
    assert ingest_tracking.get_source(path="s3://bucket/dataset_examples/images") == IngestSource(
        kind=IngestSourceKind.REMOTE, protocol="s3"
    )


@pytest.mark.parametrize(
    "path",
    [
        "/home/user/photos",
        "photos",
        "file:///home/user/photos",
        Path("/home/user/photos"),
        "/home/user/my_dataset_examples/images",
    ],
)
def test_get_source__local(path: str | Path) -> None:
    assert ingest_tracking.get_source(path=path) == IngestSource(kind=IngestSourceKind.LOCAL)


@pytest.mark.parametrize(
    "path",
    [
        "dataset_examples/coco_subset_128_images/images",
        "/home/user/dataset_examples/coco_subset_128_images/images",
        "file:///home/user/dataset_examples/coco_subset_128_images/images",
        Path("/home/user/dataset_examples/road_signs_yolo/data.yaml"),
        # The path that `quickstart_enterprise` ingests.
        "hf://datasets/lightly-ai/coco_subset_128_images/images",
    ],
)
def test_get_source__example(path: str | Path) -> None:
    assert ingest_tracking.get_source(path=path) == IngestSource(kind=IngestSourceKind.EXAMPLE)


def test_get_source__unclassifiable_path() -> None:
    class _BrokenPath:
        def __str__(self) -> str:
            raise RuntimeError("Cannot convert to string.")

    assert ingest_tracking.get_source(path=_BrokenPath()) == IngestSource(  # type: ignore[arg-type]
        kind=IngestSourceKind.UNKNOWN
    )


def test_track_samples_ingested(mocker: MockerFixture) -> None:
    mock_track = mocker.patch.object(tracking, "track")

    ingest_tracking.track_samples_ingested(
        source=IngestSource(kind=IngestSourceKind.LOCAL),
        sample_type=SampleType.IMAGE,
        ingest_format=IngestFormat.COCO,
    )

    mock_track.assert_called_once_with(
        event="samples_ingested",
        properties={"source": "local", "sample_type": "image", "format": "coco"},
    )


def test_track_samples_ingested__remote(mocker: MockerFixture) -> None:
    mock_track = mocker.patch.object(tracking, "track")

    ingest_tracking.track_samples_ingested(
        source=IngestSource(kind=IngestSourceKind.REMOTE, protocol="s3"),
        sample_type=SampleType.VIDEO,
        ingest_format=IngestFormat.FOLDER,
    )

    mock_track.assert_called_once_with(
        event="samples_ingested",
        properties={
            "source": "remote",
            "sample_type": "video",
            "format": "folder",
            "protocol": "s3",
        },
    )
