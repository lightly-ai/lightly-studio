"""Example pipeline: ingest videos, screen their quality, and tag the weak ones.

Adds videos with quality scoring enabled during ingest, then queries the resulting
quality metadata with threshold filters and puts every video that fails a screen into
its own tag, so the groups can be reviewed side by side in the GUI. Finally, near
duplicates are tagged with an embedding based deduplication pass.

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

Available variables, with their defaults:

- ``EXAMPLES_PIPELINE_VIDEOS_PATH``: folder of videos to ingest.
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

from dataclasses import dataclass

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
from lightly_studio.resolvers import video_resolver
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


# Read environment variables
env = Env()
env.read_env()

videos_path = env.path("EXAMPLES_PIPELINE_VIDEOS_PATH", DEFAULT_VIDEOS_PATH)
thresholds = _thresholds_from_env(env=env)

# Set `cleanup_existing=False` to keep the database of an earlier run.
db_manager.connect(db_file=DATABASE_FILE, cleanup_existing=True)

dataset = VideoDataset.load_or_create(name=DATASET_NAME)
# Quality scores come from the ingest decode pass, so the videos are not read twice.
dataset.add_videos_from_path(path=videos_path, embed=True, embed_frames=False, compute_quality=True)

# Query the quality metadata and tag whatever falls outside the screening thresholds.
problem_tags: list[str] = []
for tag_name, metadata_filter in build_quality_screens(thresholds=thresholds):
    tag_videos_by_metadata(dataset=dataset, metadata_filter=metadata_filter, tag_name=tag_name)
    problem_tags.append(tag_name)

# Resolution and duration live on the video sample itself, so they are matched directly
# instead of going through the metadata subquery.
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

# Every video that failed at least one screen. `tags.contains(problem_tags)` would
# instead require all of the tags at once, which only matches videos that failed every
# screen. Use that form for narrower groups, e.g.
# `tags.contains([SHAKY_CAMERA_TAG, POOR_LIGHTING_TAG])` for videos that are both shaky and dark.
failed_screen_query = dataset.query().match(
    OR(*(VideoSampleField.tags.contains(tag_name) for tag_name in problem_tags))
)
failed_screen_query.add_tag(tag_name=FAILED_SCREEN_TAG)
for video in failed_screen_query.to_list():
    print(f"Video {video.file_path_abs} failed at least one quality screen.")

# Run deduplication via the dataset query. Discarded near duplicates are tagged with
# NOT_<tag_name> and their metadata is updated with the duplicate_of and
# duplicate_of_file fields.
num_videos = len(dataset.query().to_list())
try:
    dataset.query().sampling().deduplicate(
        n_samples_to_select=num_videos,
        sampling_result_tag_name=DISTINCT_SAMPLES_TAG,
        stopping_condition_minimum_distance=thresholds.duplicate_minimum_distance,
    )
except Exception as error:
    print(f"Sampling failed: {error}")

# Report the videos that were discarded as duplicates.
duplicate_videos = dataset.query().match(
    VideoSampleField.tags.contains(f"NOT_{DISTINCT_SAMPLES_TAG}")
)
for video in duplicate_videos.to_list():
    print(
        f"Video {video.file_path_abs} was discarded as a duplicate of "
        f"{video.metadata['duplicate_of_file']}."
    )

ls.start_gui()
