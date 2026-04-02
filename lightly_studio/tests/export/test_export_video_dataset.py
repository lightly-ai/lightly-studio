from __future__ import annotations

import json
from pathlib import Path

from lightly_studio.core.video.video_dataset import VideoDataset
from lightly_studio.models.annotation.annotation_base import AnnotationCreate, AnnotationType
from lightly_studio.models.annotation.object_track import ObjectTrackCreate
from lightly_studio.resolvers import annotation_resolver, object_track_resolver
from tests.helpers_resolvers import create_annotation_label
from tests.resolvers.video.helpers import VideoStub, create_video_with_frames


class TestVideoDatasetExport:
    def test_to_youtube_vis(
        self,
        tmp_path: Path,
        patch_collection: None,  # noqa: ARG002
    ) -> None:
        dataset = VideoDataset.create(name="test_video_dataset")
        video_with_frames = create_video_with_frames(
            session=dataset.session,
            collection_id=dataset.collection_id,
            video=VideoStub(path="video_001.mp4", width=3, height=2, duration_s=2.0, fps=1.0),
        )

        label = create_annotation_label(
            session=dataset.session, root_collection_id=dataset.collection_id, label_name="cat"
        )
        object_track_id = object_track_resolver.create_many(
            session=dataset.session,
            tracks=[ObjectTrackCreate(object_track_number=99, dataset_id=dataset.dataset_id)],
        )[0]

        frame_0, frame_1 = video_with_frames.frame_sample_ids
        annotation_resolver.create_many(
            session=dataset.session,
            parent_collection_id=video_with_frames.video_frames_collection_id,
            annotations=[
                AnnotationCreate(
                    parent_sample_id=frame_0,
                    annotation_label_id=label.annotation_label_id,
                    annotation_type=AnnotationType.INSTANCE_SEGMENTATION,
                    x=0,
                    y=1,
                    width=1,
                    height=1,
                    # Row-wise RLE for a 2x3 mask with a single 1 at (row=0, col=1):
                    # row-major pixels: [0,1,0,0,0,0] -> counts [1,1,4]
                    segmentation_mask=[1, 1, 4],
                    object_track_id=object_track_id,
                ),
                AnnotationCreate(
                    parent_sample_id=frame_1,
                    annotation_label_id=label.annotation_label_id,
                    annotation_type=AnnotationType.INSTANCE_SEGMENTATION,
                    x=0,
                    y=1,
                    width=1,
                    height=1,
                    # Row-wise RLE for a 2x3 mask with a single 1 at (row=0, col=1):
                    # row-major pixels: [0,1,0,0,0,0] -> counts [1,1,4]
                    segmentation_mask=[1, 1, 4],
                    object_track_id=None,
                ),
            ],
        )

        output_json = tmp_path / "instances.json"
        dataset.export().to_youtube_vis_instance_segmentation(output_json=output_json)

        yvis = json.loads(output_json.read_text(encoding="utf-8"))
        assert yvis["categories"] == [{"id": 1, "name": "cat"}]
        assert yvis["videos"] == [
            {
                "id": 1,
                "file_names": ["video_001.mp4/00000.jpg", "video_001.mp4/00001.jpg"],
                "width": 3,
                "height": 2,
                "length": 2,
            }
        ]
        assert yvis["annotations"] == [
            {
                # id should map to object_track_id from the export input.
                "id": 99,
                "video_id": 1,
                "category_id": 1,
                "bboxes": [[0.0, 1.0, 1.0, 1.0], None],
                "segmentations": [
                    # Exported in COCO/YouTube-VIS column-major RLE:
                    # col-major pixels: [0,0,1,0,0,0] -> counts [2,1,3]
                    {"counts": [2, 1, 3], "size": [2, 3]},
                    None,
                ],
                "areas": [1.0, None],
                "iscrowd": 1,
                "height": 2,
                "width": 3,
                "length": 2,
            }
        ]
