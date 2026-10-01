"""Tests for exporting whole-video classifications to CSV."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from lightly_studio.core.video.video_dataset import VideoDataset
from lightly_studio.models.annotation.annotation_base import AnnotationType
from tests.helpers_resolvers import (
    AnnotationDetails,
    create_annotation_label,
    create_annotations,
)
from tests.resolvers.video.helpers import VideoStub, create_video


@pytest.mark.usefixtures("patch_collection")
def test_to_csv_classifications__exports_whole_video_classifications(
    tmp_path: Path,
) -> None:
    dataset = VideoDataset.create(name="video-classifications")
    video = create_video(
        session=dataset.session,
        collection_id=dataset.collection_id,
        video=VideoStub(path="/data/video.mp4"),
    )
    cat = create_annotation_label(
        session=dataset.session,
        root_collection_id=dataset.collection_id,
        label_name="cat",
    )
    selected = create_annotations(
        session=dataset.session,
        collection_id=dataset.collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=video.sample_id,
                annotation_label_id=cat.annotation_label_id,
                annotation_type=AnnotationType.CLASSIFICATION,
                confidence=0.75,
            ),
            AnnotationDetails(
                sample_id=video.sample_id,
                annotation_label_id=cat.annotation_label_id,
                annotation_type=AnnotationType.CLASSIFICATION,
                start_time_s=1.0,
                end_time_s=2.0,
            ),
        ],
        collection_name="model-v1",
    )
    create_annotations(
        session=dataset.session,
        collection_id=dataset.collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=video.sample_id,
                annotation_label_id=cat.annotation_label_id,
                annotation_type=AnnotationType.CLASSIFICATION,
            )
        ],
        collection_name="excluded-source",
    )

    output_csv = tmp_path / "classifications.csv"
    dataset.export().to_csv_classifications(
        output_csv=output_csv,
        annotation_collection_id=selected[0].annotation_collection_id,
    )

    assert _read_rows(output_csv) == [
        {
            "file_path_abs": "/data/video.mp4",
            "class_name": "cat",
            "confidence": "0.75",
            "annotation_source": "model-v1",
        }
    ]


@pytest.mark.usefixtures("patch_collection")
def test_to_csv_classifications__writes_header_for_empty_export(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dataset = VideoDataset.create(name="empty-video-classifications")
    monkeypatch.chdir(tmp_path)

    dataset.export().to_csv_classifications()

    assert (tmp_path / "classification_export.csv").read_text(encoding="utf-8") == (
        "file_path_abs,class_name,confidence,annotation_source\n"
    )


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))
