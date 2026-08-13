"""Example pipeline: ingest videos, screen their quality, and tag the weak ones.

Adds videos with quality scoring enabled during ingest, then queries the resulting
quality metadata with threshold filters and puts every video that fails a screen into
its own tag, so the groups can be reviewed side by side in the GUI. Finally, near
duplicates are tagged with an embedding based deduplication pass.

Every QA run starts by deleting all tags of the dataset, so a rerun on a kept database
only shows the tags of the current run.

Every threshold is a parameter of the run: the defaults live in ``PipelineThresholds``
and each one can be overridden with an ``EXAMPLES_PIPELINE_*`` environment variable.

Run it from the ``lightly_studio`` directory with the default thresholds::

    uv run src/lightly_studio/examples/example_pipeline.py

Screen a different folder more aggressively for blur and shake, and only keep videos
of at least 30 seconds (PowerShell)::

    $env:EXAMPLES_PIPELINE_VIDEOS_PATH = "datasets/activitynet_10_videos/videos"
    $env:EXAMPLES_PIPELINE_BLUR_SCORE_LOW_MAX = "80"
    $env:EXAMPLES_PIPELINE_SHAKE_SCORE_HIGH_MIN = "2.5"
    $env:EXAMPLES_PIPELINE_MIN_DURATION_S = "30"
    uv run src/lightly_studio/examples/example_pipeline.py

The same settings can live in a ``.env`` file in the working directory, which
``env.read_env()`` picks up automatically::

    EXAMPLES_PIPELINE_VIDEOS_PATH=datasets/activitynet_10_videos/videos
    EXAMPLES_PIPELINE_BLUR_SCORE_LOW_MAX=80
    EXAMPLES_PIPELINE_SHAKE_SCORE_HIGH_MIN=2.5
    EXAMPLES_PIPELINE_MIN_DURATION_S=30

Ingest the videos without screening them, e.g. to only fill the database::

    $env:EXAMPLES_PIPELINE_RUN_QA = "false"
    uv run src/lightly_studio/examples/example_pipeline.py

Available variables, with their defaults:

- ``EXAMPLES_PIPELINE_VIDEOS_PATH``: folder of videos to ingest.
- ``EXAMPLES_PIPELINE_RUN_QA`` (true): set to false to skip the quality assessment.
- ``EXAMPLES_PIPELINE_BLUR_SCORE_LOW_MAX`` (50.0): below this a video is blurry.
- ``EXAMPLES_PIPELINE_LIGHTING_SCORE_LOW_MAX`` (0.45): below this a video is badly lit.
- ``EXAMPLES_PIPELINE_MOTION_SCORE_LOW_MAX`` (3.0): below this the camera is static.
- ``EXAMPLES_PIPELINE_SHAKE_SCORE_HIGH_MIN`` (4.0): above this the camera is shaky.
- ``EXAMPLES_PIPELINE_MIN_WIDTH`` (1920) and ``EXAMPLES_PIPELINE_MIN_HEIGHT`` (1080).
- ``EXAMPLES_PIPELINE_MIN_DURATION_S`` (10.0): shorter videos are flagged.
- ``EXAMPLES_PIPELINE_DUPLICATE_MINIMUM_DISTANCE`` (0.5): larger values discard more
  near duplicates.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from environs import Env

import lightly_studio as ls
from lightly_studio.core.dataset_query.boolean_expression import OR
from lightly_studio.core.dataset_query.dataset_query import DatasetQuery
from lightly_studio.core.dataset_query.match_expression import MatchExpression
from lightly_studio.core.dataset_query.video_sample_field import VideoSampleField
from lightly_studio.core.video.video_dataset import VideoDataset
from lightly_studio.core.video.video_sample import VideoSample
from lightly_studio.database import db_manager
from lightly_studio.dataset import video_quality
from lightly_studio.resolvers import tag_resolver, video_resolver
from lightly_studio.resolvers.metadata_resolver.metadata_filter import Metadata, MetadataFilter
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from lightly_studio.resolvers.video_resolver.video_filter import VideoFilter

DEFAULT_VIDEOS_PATH = (
    r"D:\01_work\egocentric\lightly-studio\lightly_studio\datasets\activitynet_10_videos\videos"
)

DATABASE_FILE = "egocentric_qa.db"
DATASET_NAME = "egocentric_qa"

# Tag names written by this pipeline.
LOW_SHARPNESS_TAG = "low_sharpness"
POOR_LIGHTING_TAG = "poor_lighting"
STATIC_CAMERA_TAG = "static_camera"
SHAKY_CAMERA_TAG = "shaky_camera"
WRONG_RESOLUTION_TAG = "wrong_resolution"
SHORT_DURATION_TAG = "short_duration"
FAILED_SCREEN_TAG = "failed_quality_screen"
DISTINCT_SAMPLES_TAG = "distinct_samples"

# Custom metadata attached to individual videos, keyed by video file name. Replace this
# with whatever your own pass computes, e.g. a model output.
CUSTOM_METADATA_BY_FILE_NAME: dict[str, dict[str, Any]] = {
    "blurry_1.mp4": {"recording_site": "zurich", "operator_id": 7, "reviewed": True},
    "low_light.mp4": {"recording_site": "berlin", "operator_id": 3, "reviewed": False},
}


@dataclass(frozen=True)
class PipelineThresholds:
    """Thresholds deciding which videos this pipeline flags.

    Blur, lighting, and motion scores are "higher is better", so a video is flagged
    when it drops below the threshold. The shake score is "higher is worse", so a
    video is flagged when it goes above the threshold.

    Attributes:
        blur_score_low_max: Videos with a lower blur score are tagged as blurry.
        lighting_score_low_max: Videos with a lower lighting score are tagged as dark.
        motion_score_low_max: Videos with less motion are tagged as static.
        shake_score_high_min: Videos with more shake are tagged as shaky.
        min_width: Videos narrower than this are tagged as wrong resolution.
        min_height: Videos shorter than this in pixels are tagged as wrong resolution.
        min_duration_s: Videos shorter than this many seconds are tagged as too short.
        duplicate_minimum_distance: Minimum embedding distance between kept videos.
            Videos closer than this to an already kept video are tagged as duplicates.
    """

    blur_score_low_max: float = video_quality.DEFAULT_BLUR_SCORE_LOW_MAX
    lighting_score_low_max: float = video_quality.DEFAULT_LIGHTING_SCORE_LOW_MAX
    motion_score_low_max: float = video_quality.DEFAULT_MOTION_SCORE_LOW_MAX
    shake_score_high_min: float = video_quality.DEFAULT_SHAKE_SCORE_HIGH_MIN
    min_width: int = 1920
    min_height: int = 1080
    min_duration_s: float = 10.0
    duplicate_minimum_distance: float = 0.5


def main() -> None:
    """Ingest the videos, hand them to the QA pass, and open the GUI."""
    env = Env()
    env.read_env()

    videos_path = env.path("EXAMPLES_PIPELINE_VIDEOS_PATH", DEFAULT_VIDEOS_PATH)
    run_qa = env.bool("EXAMPLES_PIPELINE_RUN_QA", False)
    thresholds = _thresholds_from_env(env=env)

    # Set `cleanup_existing=False` to keep the database of an earlier run.
    db_manager.connect(db_file=DATABASE_FILE, cleanup_existing=False)

    dataset = VideoDataset.load_or_create(name=DATASET_NAME)
    # Read videos from the folder, compute quality scores, and embed them for deduplication.
    dataset.add_videos_from_path(
        path=videos_path, embed=True, embed_frames=False, compute_quality=True
    )
    # Insert custom calculated metadata here.
    # You could then update build_quality_screens to create tags based on that metadata.
    add_custom_metadata(dataset=dataset, metadata_by_file_name=CUSTOM_METADATA_BY_FILE_NAME)


    if run_qa:
        run_quality_assessment(dataset=dataset, thresholds=thresholds)
        ls.start_gui()


def add_custom_metadata(
    dataset: VideoDataset,
    metadata_by_file_name: Mapping[str, Mapping[str, Any]],
) -> list[VideoSample]:
    """Attach custom metadata to the videos identified by their file name.

    The key-value pairs are merged into the metadata the ingest already wrote, so the
    quality scores stay intact and existing keys are overwritten. Afterwards the values
    are filterable like any other metadata, e.g. with
    ``Metadata("operator_id") == 7`` in `query_videos_by_metadata`, and they show up in
    the GUI.

    Args:
        dataset: Video dataset holding the ingested videos.
        metadata_by_file_name: Mapping from video file name, e.g. ``"blurry_1.mp4"``, to
            the key-value pairs to store on that video. Values must be JSON
            serializable, e.g. strings, numbers, or booleans.

    Returns:
        The updated videos. File names without a matching video are skipped.
    """
    updated_videos: list[VideoSample] = []
    for file_name, metadata in metadata_by_file_name.items():
        # Match on `file_path_abs` instead if the folder holds duplicate file names.
        videos = dataset.query().match(VideoSampleField.file_name == file_name).to_list()
        if not videos:
            print(f"No video named {file_name} in the dataset, skipping its metadata.")
            continue

        for video in videos:
            # `update` merges the keys; `video.metadata["operator_id"] = 7` sets a single
            # one and returns None for keys the video does not have.
            video.metadata.update(metadata)
            values = {key: video.metadata[key] for key in metadata}
            print(f"Video {video.file_name} now has the metadata {values}.")
        updated_videos.extend(videos)

    # For many videos at once, one bulk call is faster than one update per video:
    # dataset.update_metadata([(video.sample_id, metadata), ...]).
    return updated_videos


def run_quality_assessment(dataset: VideoDataset, thresholds: PipelineThresholds) -> None:
    """Tag the videos that fail a quality screen and the near duplicates.

    Assumes the videos were ingested with ``compute_quality=True`` and ``embed=True``,
    so the quality metadata and the embeddings are already in the database.

    Args:
        dataset: Video dataset holding the ingested videos.
        thresholds: Thresholds deciding which videos are flagged.
    """
    # Start from a clean slate so a rerun does not keep the tags of an earlier run, and
    # so deduplication can recreate its result tags.
    delete_all_tags(dataset=dataset)

    problem_tags = tag_quality_problems(dataset=dataset, thresholds=thresholds)

    # Every video that failed at least one screen. `tags.contains(problem_tags)` would
    # instead require all of the tags at once, which only matches videos that failed every
    # screen. Use that form for narrower groups, e.g.
    # `tags.contains([SHAKY_CAMERA_TAG, POOR_LIGHTING_TAG])` for videos that are both shaky
    # and dark.
    failed_screen_query = dataset.query().match(
        OR(*(VideoSampleField.tags.contains(tag_name) for tag_name in problem_tags))
    )
    # failed_screen_query.add_tag(tag_name=FAILED_SCREEN_TAG)
    for video in failed_screen_query.to_list():
        print(
            f"Video {video.file_path_abs} failed at least one quality screen. "
            f"- Failures: {video.tags}"
        )

    for video in tag_near_duplicates(dataset=dataset, thresholds=thresholds):
        print(
            f"Video {video.file_path_abs} was marked discarded as a duplicate of "
            f"{video.metadata['duplicate_of_file']}."
        )


def delete_all_tags(dataset: VideoDataset) -> list[str]:
    """Delete every tag of the dataset, including the links to the tagged videos.

    Args:
        dataset: Video dataset to clear the tags of.

    Returns:
        The names of the deleted tags.
    """
    tags = tag_resolver.get_all_by_collection_id(
        session=dataset.session, collection_id=dataset.collection_id
    )
    for tag in tags:
        tag_resolver.delete(session=dataset.session, tag_id=tag.tag_id)
    return [tag.name for tag in tags]


def tag_quality_problems(dataset: VideoDataset, thresholds: PipelineThresholds) -> list[str]:
    """Tag every video that falls outside one of the screening thresholds.

    Args:
        dataset: Video dataset to screen.
        thresholds: Thresholds deciding which videos are flagged.

    Returns:
        The tag names used by the screens, in the order they were applied.
    """
    problem_tags: list[str] = []

    # Quality scores are stored as sample metadata, so they go through a subquery.
    for tag_name, metadata_filter in build_quality_screens(thresholds=thresholds):
        tag_videos_by_metadata(dataset=dataset, metadata_filter=metadata_filter, tag_name=tag_name)
        problem_tags.append(tag_name)

    # Resolution and duration live on the video sample itself, so they are matched directly.
    tag_videos_by_field(
        dataset=dataset,
        match_expression=OR(
            VideoSampleField.width < thresholds.min_width,
            VideoSampleField.height < thresholds.min_height,
        ),
        tag_name=WRONG_RESOLUTION_TAG,
    )
    problem_tags.append(WRONG_RESOLUTION_TAG)

    tag_videos_by_field(
        dataset=dataset,
        match_expression=VideoSampleField.duration_s < thresholds.min_duration_s,
        tag_name=SHORT_DURATION_TAG,
    )
    problem_tags.append(SHORT_DURATION_TAG)

    return problem_tags


def tag_near_duplicates(
    dataset: VideoDataset,
    thresholds: PipelineThresholds,
) -> list[VideoSample]:
    """Run embedding deduplication over the dataset and report what was discarded.

    Discarded near duplicates are tagged with ``NOT_<DISTINCT_SAMPLES_TAG>`` and their
    metadata is updated with the ``duplicate_of`` and ``duplicate_of_file`` fields.

    Args:
        dataset: Video dataset to deduplicate.
        thresholds: Thresholds providing the minimum embedding distance.

    Returns:
        The videos that were discarded as duplicates.
    """
    num_videos = len(dataset.query().to_list())
    try:
        dataset.query().sampling().deduplicate(
            n_samples_to_select=num_videos,
            sampling_result_tag_name=DISTINCT_SAMPLES_TAG,
            stopping_condition_minimum_distance=thresholds.duplicate_minimum_distance,
        )
    except Exception as error:
        # Deduplication needs embeddings; keep the rest of the pipeline usable without them.
        print(f"Sampling failed: {error}")
        return []

    duplicate_videos = dataset.query().match(
        VideoSampleField.tags.contains(f"NOT_{DISTINCT_SAMPLES_TAG}")
    )
    return duplicate_videos.to_list()


def build_quality_screens(thresholds: PipelineThresholds) -> list[tuple[str, MetadataFilter]]:
    """Build the metadata screens applied after ingest.

    Args:
        thresholds: Thresholds the screens compare the quality scores against.

    Returns:
        ``(tag name, metadata predicate)`` pairs, one per screened quality score.
    """
    return [
        (
            LOW_SHARPNESS_TAG,
            Metadata(video_quality.BLUR_SCORE_KEY) < thresholds.blur_score_low_max,
        ),
        (
            POOR_LIGHTING_TAG,
            Metadata(video_quality.LIGHTING_SCORE_KEY) < thresholds.lighting_score_low_max,
        ),
        (
            STATIC_CAMERA_TAG,
            Metadata(video_quality.MOTION_SCORE_KEY) < thresholds.motion_score_low_max,
        ),
        (
            SHAKY_CAMERA_TAG,
            Metadata(video_quality.SHAKE_SCORE_KEY) > thresholds.shake_score_high_min,
        ),
    ]


def query_videos_by_metadata(
    dataset: VideoDataset,
    metadata_filter: MetadataFilter,
) -> DatasetQuery[VideoSample]:
    """Build a query over the videos whose metadata matches the filter.

    Video metadata is not exposed on ``VideoSampleField``, so the predicate is resolved
    into a sample ID subquery first and then handed to the public query API.

    Args:
        dataset: Video dataset to query.
        metadata_filter: Metadata predicate, e.g. ``Metadata("blur_score") < 50``.

    Returns:
        A query yielding the matching videos.
    """
    sample_ids_subquery = video_resolver.build_sample_ids_query(
        collection_id=dataset.collection_id,
        filters=VideoFilter(sample_filter=SampleFilter(metadata_filters=[metadata_filter])),
    )
    return dataset.query().filter_by_sample_ids(sample_ids_subquery=sample_ids_subquery)


def tag_videos_by_metadata(
    dataset: VideoDataset,
    metadata_filter: MetadataFilter,
    tag_name: str,
) -> list[VideoSample]:
    """Tag every video whose metadata matches the predicate.

    The tag is created on first use and reused afterwards; videos that already carry it
    are left unchanged.

    Args:
        dataset: Video dataset to query.
        metadata_filter: Metadata predicate the videos must satisfy.
        tag_name: Name of the tag to add to the matching videos.

    Returns:
        The videos that were added to the tag.
    """
    query = query_videos_by_metadata(dataset=dataset, metadata_filter=metadata_filter)
    videos = query.to_list()
    if videos:
        query.add_tag(tag_name=tag_name)
    return videos


def tag_videos_by_field(
    dataset: VideoDataset,
    match_expression: MatchExpression,
    tag_name: str,
) -> list[VideoSample]:
    """Tag every video whose sample fields match the expression.

    Args:
        dataset: Video dataset to query.
        match_expression: Field predicate, e.g. ``VideoSampleField.duration_s < 10``.
        tag_name: Name of the tag to add to the matching videos.

    Returns:
        The videos that were added to the tag.
    """
    query = dataset.query().match(match_expression)
    videos = query.to_list()
    if videos:
        query.add_tag(tag_name=tag_name)
    return videos


def _thresholds_from_env(env: Env) -> PipelineThresholds:
    """Read the thresholds from the environment, falling back to the defaults."""
    defaults = PipelineThresholds()
    return PipelineThresholds(
        blur_score_low_max=env.float(
            "EXAMPLES_PIPELINE_BLUR_SCORE_LOW_MAX", defaults.blur_score_low_max
        ),
        lighting_score_low_max=env.float(
            "EXAMPLES_PIPELINE_LIGHTING_SCORE_LOW_MAX", defaults.lighting_score_low_max
        ),
        motion_score_low_max=env.float(
            "EXAMPLES_PIPELINE_MOTION_SCORE_LOW_MAX", defaults.motion_score_low_max
        ),
        shake_score_high_min=env.float(
            "EXAMPLES_PIPELINE_SHAKE_SCORE_HIGH_MIN", defaults.shake_score_high_min
        ),
        min_width=env.int("EXAMPLES_PIPELINE_MIN_WIDTH", defaults.min_width),
        min_height=env.int("EXAMPLES_PIPELINE_MIN_HEIGHT", defaults.min_height),
        min_duration_s=env.float("EXAMPLES_PIPELINE_MIN_DURATION_S", defaults.min_duration_s),
        duplicate_minimum_distance=env.float(
            "EXAMPLES_PIPELINE_DUPLICATE_MINIMUM_DISTANCE", defaults.duplicate_minimum_distance
        ),
    )


if __name__ == "__main__":
    main()
