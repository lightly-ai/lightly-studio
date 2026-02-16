from __future__ import annotations

import json
from pathlib import Path

import pytest

from lightly_studio.core.video.video_dataset import VideoDataset
from lightly_studio.dataset.embedding_manager import EmbeddingManagerProvider
from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.resolvers import annotation_resolver, sample_embedding_resolver, video_resolver
from tests.resolvers.video.helpers import create_video_file


class TestDataset:
    def test_dataset_add_videos_from_path__valid(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        create_video_file(
            output_path=tmp_path / "test_video_1.mp4",
            width=640,
            height=480,
            num_frames=30,
            fps=2,
        )
        create_video_file(
            output_path=tmp_path / "test_video_0.mp4",
            width=640,
            height=480,
            num_frames=30,
            fps=2,
        )

        dataset = VideoDataset.create(name="test_dataset")
        dataset.add_videos_from_path(path=tmp_path)

        # Verify frames are in the database
        videos = video_resolver.get_all_by_collection_id(
            session=dataset.session,
            collection_id=dataset.dataset_id,
        ).samples
        assert len(videos) == 2
        assert {s.file_name for s in videos} == {
            "test_video_1.mp4",
            "test_video_0.mp4",
        }
        # Check that embeddings were created
        embedding_manager = EmbeddingManagerProvider.get_embedding_manager()
        model_id = embedding_manager.load_or_get_default_model(
            session=dataset.session,
            collection_id=dataset.dataset_id,
        )
        assert model_id is not None
        embeddings = sample_embedding_resolver.get_all_by_collection_id(
            session=dataset.session, collection_id=dataset.dataset_id, embedding_model_id=model_id
        )
        assert len(embeddings) == 2

    def test_dataset_add_videos_from_path__dont_embed(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        create_video_file(
            output_path=tmp_path / "test_video_1.mp4",
            width=640,
            height=480,
            num_frames=30,
            fps=2,
        )
        create_video_file(
            output_path=tmp_path / "test_video_0.mp4",
            width=640,
            height=480,
            num_frames=30,
            fps=2,
        )

        dataset = VideoDataset.create(name="test_dataset")
        dataset.add_videos_from_path(path=tmp_path, embed=False)

        # Verify frames are in the database
        videos = video_resolver.get_all_by_collection_id(
            session=dataset.session,
            collection_id=dataset.dataset_id,
        ).samples
        assert len(videos) == 2
        assert {s.file_name for s in videos} == {
            "test_video_1.mp4",
            "test_video_0.mp4",
        }
        # Check that embeddings were created
        embedding_manager = EmbeddingManagerProvider.get_embedding_manager()
        model_id = embedding_manager.load_or_get_default_model(
            session=dataset.session,
            collection_id=dataset.dataset_id,
        )
        assert model_id is not None
        embeddings = sample_embedding_resolver.get_all_by_collection_id(
            session=dataset.session, collection_id=dataset.dataset_id, embedding_model_id=model_id
        )
        assert len(embeddings) == 0

    def test_add_videos_from_youtube_vis__object_detection(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        # Create a video file.
        create_video_file(
            output_path=tmp_path / "video_001.mp4",
            width=640,
            height=480,
            num_frames=2,
            fps=1,
        )

        # Create a YouTube-VIS style annotations JSON.
        annotations = {
            "info": {"description": "Test dataset"},
            "categories": [
                {"id": 1, "name": "cat"},
                {"id": 2, "name": "dog"},
            ],
            "videos": [
                {
                    "id": 1,
                    "file_names": ["video_001/00000.jpg", "video_001/00001.jpg"],
                    "width": 640,
                    "height": 480,
                    "length": 2,
                }
            ],
            "annotations": [
                {
                    "id": 1,
                    "video_id": 1,
                    "category_id": 1,
                    "bboxes": [[10.0, 20.0, 30.0, 40.0], [15.0, 25.0, 35.0, 45.0]],
                    "areas": [1200.0, 1575.0],
                },
            ],
        }
        annotations_path = tmp_path / "annotations.json"
        annotations_path.write_text(json.dumps(annotations))

        dataset = VideoDataset.create(name="test_dataset")
        dataset.add_videos_from_youtube_vis(
            annotations_json=annotations_path,
            videos_path=tmp_path,
            annotation_type=AnnotationType.OBJECT_DETECTION,
            embed=False,
        )

        # Verify videos are in the database.
        videos = video_resolver.get_all_by_collection_id(
            session=dataset.session,
            collection_id=dataset.dataset_id,
        ).samples
        assert len(videos) == 1
        assert videos[0].file_name == "video_001.mp4"

        # Verify annotations were created.
        all_annotations = annotation_resolver.get_all(dataset.session).annotations
        assert len(all_annotations) == 2
        assert all(a.annotation_type == "object_detection" for a in all_annotations)

    def test_add_videos_from_youtube_vis__instance_segmentation(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        # Create a video file.
        create_video_file(
            output_path=tmp_path / "video_001.mp4",
            width=4,
            height=4,
            num_frames=2,
            fps=1,
        )

        # Create a YouTube-VIS style annotations JSON with segmentation.
        annotations = {
            "info": {"description": "Test dataset"},
            "categories": [
                {"id": 1, "name": "cat"},
            ],
            "videos": [
                {
                    "id": 1,
                    "file_names": ["video_001/00000.jpg", "video_001/00001.jpg"],
                    "width": 4,
                    "height": 4,
                    "length": 2,
                }
            ],
            "annotations": [
                {
                    "id": 1,
                    "video_id": 1,
                    "category_id": 1,
                    "segmentations": [
                        [[0, 0, 1, 1, 2, 1]],
                        [[0, 0, 1, 1, 2, 1]],
                    ],
                    "bboxes": [[1.0, 1.0, 1.0, 1.0], [2.0, 2.0, 2.0, 2.0]],
                    "areas": [4.0, 4.0],
                },
            ],
        }
        annotations_path = tmp_path / "annotations.json"
        annotations_path.write_text(json.dumps(annotations))

        dataset = VideoDataset.create(name="test_dataset")
        dataset.add_videos_from_youtube_vis(
            annotations_json=annotations_path,
            videos_path=tmp_path,
            annotation_type=AnnotationType.INSTANCE_SEGMENTATION,
            embed=False,
        )

        # Verify videos are in the database.
        videos = video_resolver.get_all_by_collection_id(
            session=dataset.session,
            collection_id=dataset.dataset_id,
        ).samples
        assert len(videos) == 1

        # Verify annotations were created.
        all_annotations = annotation_resolver.get_all(dataset.session).annotations
        assert len(all_annotations) == 2
        assert all(a.annotation_type == "instance_segmentation" for a in all_annotations)

    def test_add_videos_from_youtube_vis__multiple_videos_same_stem(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        # Create two video files with the same stem but different extensions,
        # plus one additional video with a different stem.
        create_video_file(
            output_path=tmp_path / "video_001.mp4",
            width=640,
            height=480,
            num_frames=2,
            fps=1,
        )
        create_video_file(
            output_path=tmp_path / "video_001.mov",
            width=640,
            height=480,
            num_frames=2,
            fps=1,
        )
        create_video_file(
            output_path=tmp_path / "video_002.mp4",
            width=640,
            height=480,
            num_frames=3,
            fps=1,
        )

        # Create annotations
        annotations = {
            "info": {"description": "Test dataset"},
            "categories": [{"id": 1, "name": "cat"}],
            "videos": [
                {
                    "id": 1,
                    "file_names": ["video_001/00000.jpg", "video_001/00001.jpg"],
                    "width": 640,
                    "height": 480,
                    "length": 2,
                },
                {
                    "id": 2,
                    "file_names": [
                        "video_002/00000.jpg",
                        "video_002/00001.jpg",
                        "video_002/00002.jpg",
                    ],
                    "width": 640,
                    "height": 480,
                    "length": 3,
                },
            ],
            "annotations": [
                {
                    "id": 1,
                    "video_id": 1,
                    "category_id": 1,
                    "bboxes": [[10.0, 20.0, 30.0, 40.0], [15.0, 25.0, 35.0, 45.0]],
                    "areas": [1200.0, 1575.0],
                },
                {
                    "id": 2,
                    "video_id": 2,
                    "category_id": 1,
                    "bboxes": [[5.0, 5.0, 10.0, 10.0], [6.0, 6.0, 11.0, 11.0], None],
                    "areas": [100.0, 121.0, None],
                },
            ],
        }
        annotations_path = tmp_path / "annotations.json"
        annotations_path.write_text(json.dumps(annotations))

        dataset = VideoDataset.create(name="test_dataset")
        with pytest.raises(ValueError, match="Duplicate video path"):
            dataset.add_videos_from_youtube_vis(
                annotations_json=annotations_path,
                videos_path=tmp_path,
                annotation_type=AnnotationType.OBJECT_DETECTION,
                embed=False,
            )

    def test_add_videos_from_youtube_vis__with_embedding(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        # Create a video file.
        create_video_file(
            output_path=tmp_path / "video_001.mp4",
            width=640,
            height=480,
            num_frames=2,
            fps=1,
        )

        # Create a YouTube-VIS style annotations JSON.
        annotations = {
            "info": {"description": "Test dataset"},
            "categories": [{"id": 1, "name": "cat"}],
            "videos": [
                {
                    "id": 1,
                    "file_names": ["video_001/00000.jpg", "video_001/00001.jpg"],
                    "width": 640,
                    "height": 480,
                    "length": 2,
                }
            ],
            "annotations": [
                {
                    "id": 1,
                    "video_id": 1,
                    "category_id": 1,
                    "bboxes": [[10.0, 20.0, 30.0, 40.0], None],
                    "areas": [1200.0, None],
                },
            ],
        }
        annotations_path = tmp_path / "annotations.json"
        annotations_path.write_text(json.dumps(annotations))

        dataset = VideoDataset.create(name="test_dataset")
        dataset.add_videos_from_youtube_vis(
            annotations_json=annotations_path,
            videos_path=tmp_path,
            annotation_type=AnnotationType.OBJECT_DETECTION,
            embed=True,
        )

        # Verify embeddings were created
        embedding_manager = EmbeddingManagerProvider.get_embedding_manager()
        model_id = embedding_manager.load_or_get_default_model(
            session=dataset.session,
            collection_id=dataset.dataset_id,
        )
        assert model_id is not None
        embeddings = sample_embedding_resolver.get_all_by_collection_id(
            session=dataset.session, collection_id=dataset.dataset_id, embedding_model_id=model_id
        )
        assert len(embeddings) == 1

    def test_add_videos_from_youtube_vis__invalid_file(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        dataset = VideoDataset.create(name="test_dataset")

        # Test with non-existent file.
        with pytest.raises(FileNotFoundError, match="YouTube-VIS annotations json file not found"):
            dataset.add_videos_from_youtube_vis(
                annotations_json=tmp_path / "nonexistent.json",
                videos_path=tmp_path,
            )

        # Test with non-JSON file.
        non_json_file = tmp_path / "annotations.txt"
        non_json_file.write_text("not a json file")
        with pytest.raises(FileNotFoundError, match="YouTube-VIS annotations json file not found"):
            dataset.add_videos_from_youtube_vis(
                annotations_json=non_json_file,
                videos_path=tmp_path,
            )

    def test_add_videos_from_youtube_vis__invalid_annotation_type(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        # Create a minimal JSON file.
        annotations_path = tmp_path / "annotations.json"
        annotations_path.write_text(
            json.dumps({"info": {}, "categories": [], "videos": [], "annotations": []})
        )

        dataset = VideoDataset.create(name="test_dataset")

        with pytest.raises(ValueError, match="Invalid annotation type"):
            dataset.add_videos_from_youtube_vis(
                annotations_json=annotations_path,
                videos_path=tmp_path,
                annotation_type=AnnotationType.SEMANTIC_SEGMENTATION,
            )
