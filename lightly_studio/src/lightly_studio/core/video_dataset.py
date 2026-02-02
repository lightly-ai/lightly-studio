"""LightlyStudio VideoDataset."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable
from uuid import UUID

from labelformat.formats import (
    YouTubeVISInstanceSegmentationTrackInput,
    YouTubeVISObjectDetectionTrackInput,
)
from sqlmodel import Session

from lightly_studio.core import add_videos
from lightly_studio.core.add_videos import VIDEO_EXTENSIONS
from lightly_studio.core.dataset import BaseSampleDataset
from lightly_studio.core.video_sample import VideoSample
from lightly_studio.dataset import fsspec_lister
from lightly_studio.dataset.embedding_manager import EmbeddingManagerProvider
from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import video_resolver
from lightly_studio.type_definitions import PathLike

logger = logging.getLogger(__name__)


class VideoDataset(BaseSampleDataset[VideoSample]):
    """Video dataset.

    It can be created or loaded using one of the static methods:
    ```python
    dataset = VideoDataset.create()
    dataset = VideoDataset.load()
    dataset = VideoDataset.load_or_create()
    ```

    Samples can be added to the dataset using:
    ```python
    dataset.add_videos_from_path(...)
    ```

    The dataset samples can be queried directly by iterating over it or slicing it:
    ```python
    dataset = VideoDataset.load("my_dataset")
    first_ten_samples = dataset[:10]
    for sample in dataset:
        print(sample.file_name)
        sample.metadata["new_key"] = "new_value"
    ```

    For filtering or ordering samples first, use the query interface:
    ```python
    from lightly_studio.core.dataset_query.video_sample_field import VideoSampleField

    dataset = VideoDataset.load("my_dataset")
    query = dataset.match(VideoSampleField.width > 10).order_by(VideoSampleField.file_name)
    for sample in query:
        ...
    ```
    """

    @staticmethod
    def sample_type() -> SampleType:
        """Returns the sample type."""
        return SampleType.VIDEO

    @staticmethod
    def sample_class() -> type[VideoSample]:
        """Returns the sample class."""
        return VideoSample

    def get_sample(self, sample_id: UUID) -> VideoSample:
        """Get a single sample from the dataset by its ID.

        Args:
            sample_id: The UUID of the sample to retrieve.

        Returns:
            A single VideoSample object.

        Raises:
            IndexError: If no sample is found with the given sample_id.
        """
        sample = video_resolver.get_by_id(self.session, sample_id=sample_id)

        if sample is None:
            raise IndexError(f"No sample found for sample_id: {sample_id}")
        return VideoSample(inner=sample)

    def add_videos_from_path(
        self,
        path: PathLike,
        allowed_extensions: Iterable[str] | None = None,
        num_decode_threads: int | None = None,
        embed: bool = True,
    ) -> None:
        """Adding video frames from the specified path to the dataset.

        Args:
            path: Path to the folder containing the videos to add.
            allowed_extensions: An iterable container of allowed video file
                extensions in lowercase, including the leading dot. If None,
                uses default VIDEO_EXTENSIONS.
            num_decode_threads: Optional override for the number of FFmpeg decode threads.
                If omitted, the available CPU cores - 1 (max 16) are used.
            embed: If True, generate embeddings for the newly added videos.
        """
        video_paths = _collect_video_file_paths(path=path, allowed_extensions=allowed_extensions)
        logger.info(f"Found {len(video_paths)} videos in {path}.")

        # Process videos.
        created_sample_ids, _ = add_videos.load_into_dataset_from_paths(
            session=self.session,
            dataset_id=self.dataset_id,
            video_paths=video_paths,
            num_decode_threads=num_decode_threads,
        )

        if embed:
            _generate_embeddings_video(
                session=self.session,
                dataset_id=self.dataset_id,
                sample_ids=created_sample_ids,
            )

    def add_samples_from_youtube_vis(
        self,
        annotations_json: PathLike,
        path: PathLike,
        num_decode_threads: int | None = None,
        annotation_type: AnnotationType = AnnotationType.OBJECT_DETECTION,
        embed: bool = True,
    ) -> None:
        """Load videos and YouTube-VIS annotations and store them in the database.

        Args:
            annotations_json: Path to the YouTube-VIS annotations JSON file.
            path: Path to the folder containing the videos.
            num_decode_threads: Optional override for the number of FFmpeg decode threads.
            annotation_type: The type of annotation to be loaded (e.g., 'ObjectDetection',
                'InstanceSegmentation').
            embed: If True, generate embeddings for the newly added videos.
        """
        if isinstance(annotations_json, str):
            annotations_json = Path(annotations_json)
        annotations_json = annotations_json.absolute()

        if not annotations_json.is_file() or annotations_json.suffix != ".json":
            raise FileNotFoundError(
                f"YouTube-VIS annotations json file not found: '{annotations_json}'"
            )
        label_input: YouTubeVISObjectDetectionTrackInput | YouTubeVISInstanceSegmentationTrackInput
        if annotation_type == AnnotationType.OBJECT_DETECTION:
            label_input = YouTubeVISObjectDetectionTrackInput(input_file=annotations_json)
        elif annotation_type == AnnotationType.INSTANCE_SEGMENTATION:
            label_input = YouTubeVISInstanceSegmentationTrackInput(input_file=annotations_json)
        else:
            raise ValueError(f"Invalid annotation type: {annotation_type}")

        video_paths = _resolve_video_paths_from_labelformat(
            input_labels=label_input, videos_path=path
        )

        created_sample_ids, _ = add_videos.load_into_dataset_from_paths(
            session=self.session,
            dataset_id=self.dataset_id,
            video_paths=video_paths,
            num_decode_threads=num_decode_threads,
        )

        add_videos.load_video_annotations_from_labelformat(
            session=self.session,
            dataset_id=self.dataset_id,
            input_labels=label_input,
        )

        if embed:
            _generate_embeddings_video(
                session=self.session,
                dataset_id=self.dataset_id,
                sample_ids=created_sample_ids,
            )



def _generate_embeddings_video(
    session: Session,
    dataset_id: UUID,
    sample_ids: list[UUID],
) -> None:
    """Generate and store embeddings for samples.

    Args:
        session: Database session for resolver operations.
        dataset_id: The ID of the dataset to associate with the embedding model.
        sample_ids: List of sample IDs to generate embeddings for.
    """
    if not sample_ids:
        return

    embedding_manager = EmbeddingManagerProvider.get_embedding_manager()
    model_id = embedding_manager.load_or_get_default_model(
        session=session, collection_id=dataset_id
    )
    if model_id is None:
        logger.warning("No embedding model loaded. Skipping embedding generation.")
        return

    embedding_manager.embed_videos(
        session=session,
        collection_id=dataset_id,
        sample_ids=sample_ids,
        embedding_model_id=model_id,
    )

def _collect_video_file_paths(
    path: PathLike,
    allowed_extensions: Iterable[str] | None = None,
) -> list[str]:
    # Collect video file paths.
    if allowed_extensions:
        allowed_extensions_set = {ext.lower() for ext in allowed_extensions}
    else:
        allowed_extensions_set = VIDEO_EXTENSIONS
    return list(
        fsspec_lister.iter_files_from_path(
            path=str(path), allowed_extensions=allowed_extensions_set
        )
    )

def _resolve_video_paths_from_labelformat(
    input_labels: YouTubeVISObjectDetectionTrackInput | YouTubeVISInstanceSegmentationTrackInput,
    videos_path: PathLike,
    allowed_extensions: Iterable[str] | None = None,
) -> list[str]:
    """Resolve video paths from a labelformat input."""
    media_items = input_labels.get_videos()

    videos_path = Path(videos_path)

    video_paths = []
    video_index = _index_video_paths(videos_path=videos_path, allowed_extensions=allowed_extensions)
    for media in media_items:
        filename = Path(media.filename)
        if filename.suffix:
            resolved_path = str(videos_path / filename)
        else:
            resolved_path = video_index[filename.stem]
        if resolved_path is None:
            raise FileNotFoundError(f"No video file found for '{filename}' under '{videos_path}'.")
        video_paths.append(resolved_path)
    return list(dict.fromkeys(video_paths))


def _index_video_paths(
    videos_path: PathLike,
    allowed_extensions: Iterable[str] | None = None,
) -> dict[str, str]:
    """Index video paths by filename and stem for suffix-free matching."""
    index: dict[str, str] = {}
    video_files = _collect_video_file_paths(path=videos_path, allowed_extensions=allowed_extensions)
    for video_file in video_files:
        file_path = Path(video_file)
        index[file_path.stem] = str(file_path.absolute())
    return index
