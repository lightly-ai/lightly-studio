"""Tests for the frame-specific export wiring in `video_frame_dataset_export`.

The sample-type-agnostic export format logic is tested in the `test_dataset_export__*.py`
files. Here we only cover what is frame-specific: the `video_frame_to_image` mapping,
`to_image_files`, and that `VideoFrameDataset.export()` uses it and forwards the query.
"""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image as PILImage
from pytest_mock import MockerFixture

from lightly_studio.core.dataset_query import VideoFrameSampleField
from lightly_studio.core.video.video_dataset import VideoDataset
from lightly_studio.export import video_frame_dataset_export
from lightly_studio.models.annotation.annotation_base import (
    AnnotationCreate,
    AnnotationType,
)
from lightly_studio.resolvers import annotation_resolver
from tests.helpers_resolvers import create_annotation_label
from tests.resolvers.video.helpers import (
    VideoStub,
    create_video_file,
    create_video_with_frames,
)


def _create_dataset_with_local_video(tmp_path: Path, *, num_frames: int = 3) -> VideoDataset:
    """Create a video dataset backed by a real local mp4 with ``num_frames`` frames."""
    dataset = VideoDataset.create(name="test_video_dataset")
    video_path = tmp_path / "test_video.mp4"
    create_video_file(video_path, width=100, height=100, num_frames=num_frames, fps=30)
    create_video_with_frames(
        session=dataset.session,
        collection_id=dataset.collection_id,
        video=VideoStub(
            path=str(video_path),
            width=100,
            height=100,
            duration_s=num_frames / 30.0,
            fps=30.0,
        ),
    )
    return dataset


class TestVideoFrameDatasetExport:
    def test_export__forwards_query_and_maps_frame_samples(
        self,
        tmp_path: Path,
        patch_collection: None,  # noqa: ARG002
    ) -> None:
        """Tests that `VideoFrameDataset.export(query)` forwards the query and maps frames.

        The exported frames are filtered by the query and referenced by a file name synthesized
        from the parent video's absolute path and the frame number, with the video's dimensions.
        """
        dataset = VideoDataset.create(name="test_video_dataset")
        video_with_frames = create_video_with_frames(
            session=dataset.session,
            collection_id=dataset.collection_id,
            video=VideoStub(
                path="/abs/dir/video_001.mp4", width=3, height=2, duration_s=2.0, fps=1.0
            ),
        )
        label = create_annotation_label(
            session=dataset.session, root_collection_id=dataset.collection_id, label_name="dog"
        )
        frame_0 = video_with_frames.frame_sample_ids[0]
        annotation_resolver.create_many(
            session=dataset.session,
            parent_collection_id=video_with_frames.video_frames_collection_id,
            annotations=[
                AnnotationCreate(
                    parent_sample_id=frame_0,
                    annotation_label_id=label.annotation_label_id,
                    annotation_type=AnnotationType.OBJECT_DETECTION,
                    x=0,
                    y=1,
                    width=1,
                    height=1,
                ),
            ],
        )

        output_json = tmp_path / "coco.json"
        frames = dataset.frames()
        query = frames.query().match(VideoFrameSampleField.frame_number <= 0)
        frames.export(query).to_coco_object_detections(output_json=output_json)

        with open(output_json) as f:
            coco_data = json.load(f)
        # Only frame 0 matches the query; it is referenced by the parent video's absolute path
        # and the frame number, with the parent video's dimensions.
        assert coco_data["images"] == [
            {"id": 0, "file_name": "/abs/dir/video_001.mp4/000000000.jpg", "width": 3, "height": 2},
        ]

    def test_to_image_files__exports_frames_locally(
        self,
        tmp_path: Path,
        patch_collection: None,  # noqa: ARG002
    ) -> None:
        """Exports all frames as PNGs and creates the output directory if needed."""
        dataset = _create_dataset_with_local_video(tmp_path, num_frames=3)
        output_dir = tmp_path / "new_directory" / "frames"
        assert not output_dir.exists()

        frames = dataset.frames()
        frames.export(frames.query()).to_image_files(output_dir=output_dir)

        exported_files = sorted(output_dir.glob("*.png"))
        assert [path.name for path in exported_files] == [
            "test_video-0-mp4.png",
            "test_video-1-mp4.png",
            "test_video-2-mp4.png",
        ]
        for image_file in exported_files:
            with PILImage.open(image_file) as img:
                assert img.size == (100, 100)

    def test_to_image_files__respects_query_filter(
        self,
        tmp_path: Path,
        patch_collection: None,  # noqa: ARG002
    ) -> None:
        """Only exports frames matching the query."""
        dataset = _create_dataset_with_local_video(tmp_path, num_frames=3)
        output_dir = tmp_path / "exported_frames"
        frames = dataset.frames()
        query = frames.query().match(VideoFrameSampleField.frame_number == 0)
        frames.export(query).to_image_files(output_dir=output_dir)

        exported_files = list(output_dir.glob("*.png"))
        assert len(exported_files) == 1
        assert exported_files[0].name == "test_video-0-mp4.png"


def test_video_frame_to_image__coco_uses_absolute_video_path(
    patch_collection: None,  # noqa: ARG001
) -> None:
    """COCO exports reference the absolute video path and the frame number."""
    dataset = VideoDataset.create(name="test_video_dataset")
    create_video_with_frames(
        session=dataset.session,
        collection_id=dataset.collection_id,
        video=VideoStub(
            path="/abs/dir/video_001.mp4", width=640, height=480, duration_s=1.0, fps=1.0
        ),
    )
    frame = next(iter(dataset.frames()))

    image = video_frame_dataset_export.video_frame_to_image(
        sample=frame, image_id=7, use_relative_filename=False
    )

    assert image.id == 7
    assert image.filename == "/abs/dir/video_001.mp4/000000000.jpg"
    assert image.width == 640
    assert image.height == 480


def test_video_frame_to_image__yolo_pascal_use_relative_video_name(
    patch_collection: None,  # noqa: ARG001
) -> None:
    """YOLO and Pascal VOC exports reference the relative video name and the frame number."""
    dataset = VideoDataset.create(name="test_video_dataset")
    create_video_with_frames(
        session=dataset.session,
        collection_id=dataset.collection_id,
        video=VideoStub(
            path="/abs/dir/video_001.mp4", width=640, height=480, duration_s=1.0, fps=1.0
        ),
    )
    frame = next(iter(dataset.frames()))

    image = video_frame_dataset_export.video_frame_to_image(
        sample=frame, image_id=7, use_relative_filename=True
    )

    assert image.id == 7
    assert image.filename == "video_001.mp4/000000000.jpg"
    assert image.width == 640
    assert image.height == 480


def test_video_frame_filename() -> None:
    assert (
        video_frame_dataset_export._video_frame_filename(
            video_filename="video_001.mp4",
            decode_index=7,
            zero_padding=2,
            file_extension="jpg",
        )
        == "video_001-07-mp4.jpg"
    )


def test_frame_to_pil_image__applies_rotation(mocker: MockerFixture) -> None:
    pil_image = PILImage.new("RGB", (20, 10), color=(255, 0, 0))
    frame = mocker.MagicMock()
    frame.to_image.return_value = pil_image

    rotated = video_frame_dataset_export._frame_to_pil_image(frame=frame, rotation_deg=90)

    assert rotated.size == (10, 20)
