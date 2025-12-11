from __future__ import annotations

from pathlib import Path

from lightly_studio import Dataset
from lightly_studio.dataset.embedding_manager import EmbeddingManagerProvider
from lightly_studio.models.dataset import SampleType
from lightly_studio.resolvers import sample_embedding_resolver, video_resolver
from tests.core.test_add_videos import _create_temp_video


class TestDataset:
    def test_dataset_add_videos_from_path__valid(
        self,
        patch_dataset: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        _create_temp_video(
            output_path=tmp_path / "test_video_1.mp4",
            width=640,
            height=480,
            num_frames=30,
            fps=2,
        )
        _create_temp_video(
            output_path=tmp_path / "test_video_0.mp4",
            width=640,
            height=480,
            num_frames=30,
            fps=2,
        )

        dataset = Dataset.create(name="test_dataset", sample_type=SampleType.VIDEO)
        dataset.add_videos_from_path(path=tmp_path)

        # Verify frames are in the database
        videos = video_resolver.get_all_by_dataset_id(
            session=dataset.session,
            dataset_id=dataset.dataset_id,
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
            dataset_id=dataset.dataset_id,
        )
        assert model_id is not None
        embeddings = sample_embedding_resolver.get_all_by_dataset_id(
            session=dataset.session, dataset_id=dataset.dataset_id, embedding_model_id=model_id
        )
        assert len(embeddings) == 2

    def test_dataset_add_videos_from_path__dont_embed(
        self,
        patch_dataset: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        _create_temp_video(
            output_path=tmp_path / "test_video_1.mp4",
            width=640,
            height=480,
            num_frames=30,
            fps=2,
        )
        _create_temp_video(
            output_path=tmp_path / "test_video_0.mp4",
            width=640,
            height=480,
            num_frames=30,
            fps=2,
        )

        dataset = Dataset.create(name="test_dataset", sample_type=SampleType.VIDEO)
        dataset.add_videos_from_path(path=tmp_path, embed=False)

        # Verify frames are in the database
        videos = video_resolver.get_all_by_dataset_id(
            session=dataset.session,
            dataset_id=dataset.dataset_id,
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
            dataset_id=dataset.dataset_id,
        )
        assert model_id is not None
        embeddings = sample_embedding_resolver.get_all_by_dataset_id(
            session=dataset.session, dataset_id=dataset.dataset_id, embedding_model_id=model_id
        )
        assert len(embeddings) == 0
