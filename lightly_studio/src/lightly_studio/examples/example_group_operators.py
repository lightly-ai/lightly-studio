"""Example combining a group dataset with operators for every supported scope.

Demonstrates how operators are surfaced contextually in the GUI depending on which
sub-collection (images, videos, frames, groups) the user is currently viewing.

Dataset layout (MIDV-style):
  - photo         — IMAGE sub-collection
  - scan_upright  — IMAGE sub-collection
  - clips_video   — VIDEO sub-collection  (frames accessible via the Frames view)

Registered operators:
  - ROOT             Export Dataset Manifest        (dataset-level summary)
  - IMAGE            Flag Low-Quality Images        (image collections / single image)
  - VIDEO_FRAME      Sample Keyframes               (frame collections / single frame)
  - VIDEO            Extract Video Metadata         (video collections / single video)
  - GROUP            Validate Group Completeness    (group items)
  - IMAGE+FRAME      Compute Embedding Statistics   (images and frames alike)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from environs import Env
from sqlmodel import Session

import lightly_studio as ls
from lightly_studio import db_manager
from lightly_studio.plugins.base_operator import BaseOperator, OperatorResult
from lightly_studio.plugins.operator_context import ExecutionContext, OperatorScope
from lightly_studio.plugins.operator_registry import operator_registry
from lightly_studio.plugins.parameter import (
    BaseParameter,
    BoolParameter,
    FloatParameter,
    IntParameter,
    StringParameter,
)


# ---------------------------------------------------------------------------
# ROOT — dataset-level
# Applicable: dataset home / root collection view.
# Not applicable: any typed sub-collection (images, videos, frames, groups).
# ---------------------------------------------------------------------------


@dataclass
class ExportDatasetManifestOperator(BaseOperator):
    """Export a top-level manifest summarising every sub-collection in the dataset."""

    name: str = "Export Dataset Manifest [ROOT]"
    description: str = (
        "Writes a JSON manifest listing all sub-collections and their sample counts. "
        "Only applicable at the root/dataset level."
    )

    @property
    def parameters(self) -> list[BaseParameter]:
        """Return operator parameters."""
        return [
            StringParameter(
                name="output_path",
                required=True,
                default="/tmp/manifest.json",
                description="File path where the manifest JSON will be written.",
            ),
        ]

    @property
    def supported_scopes(self) -> list[OperatorScope]:
        """Support root scope only."""
        return [OperatorScope.ROOT]

    def execute(
        self,
        *,
        session: Session,  # noqa: ARG002
        context: ExecutionContext,
        parameters: dict[str, Any],
    ) -> OperatorResult:
        """Execute the operator."""
        output_path = parameters.get("output_path", "/tmp/manifest.json")
        return OperatorResult(
            success=True,
            message=(
                f"Dataset manifest for collection {context.collection_id} "
                f"written to '{output_path}'."
            ),
        )


# ---------------------------------------------------------------------------
# IMAGE — image sub-collections
# Applicable: Samples page (full collection, filtered subset, or single image).
# Not applicable: Videos, Frames, Groups pages.
# ---------------------------------------------------------------------------


@dataclass
class FlagLowQualityImagesOperator(BaseOperator):
    """Tag images whose quality score falls below a configurable threshold."""

    name: str = "Flag Low-Quality Images [IMAGE]"
    description: str = (
        "Assigns a tag to every image in scope whose estimated quality score is below "
        "the threshold. Respects the active filter — run on the full collection, a "
        "filtered subset, or a single selected image."
    )

    @property
    def parameters(self) -> list[BaseParameter]:
        """Return operator parameters."""
        return [
            FloatParameter(
                name="quality_threshold",
                required=True,
                default=0.4,
                description="Images with a quality score below this value will be flagged (0–1).",
            ),
            StringParameter(
                name="tag_name",
                required=True,
                default="low-quality",
                description="Tag that will be assigned to flagged images.",
            ),
        ]

    @property
    def supported_scopes(self) -> list[OperatorScope]:
        """Support image scope."""
        return [OperatorScope.IMAGE]

    def execute(
        self,
        *,
        session: Session,  # noqa: ARG002
        context: ExecutionContext,
        parameters: dict[str, Any],
    ) -> OperatorResult:
        """Execute the operator."""
        threshold = parameters.get("quality_threshold", 0.4)
        tag = parameters.get("tag_name", "low-quality")
        scope = "filtered subset" if context.context_filter is not None else "full collection"
        return OperatorResult(
            success=True,
            message=(
                f"Flagged images below quality {threshold} with tag '{tag}' "
                f"across {scope} of collection {context.collection_id}."
            ),
        )


# ---------------------------------------------------------------------------
# VIDEO_FRAME — frame sub-collections
# Applicable: Frames page (full frame collection, filtered frames, or single frame).
# Not applicable: Samples, Videos, Groups pages.
# ---------------------------------------------------------------------------


@dataclass
class SampleKeyframesOperator(BaseOperator):
    """Select a representative set of keyframes from the frames in scope."""

    name: str = "Sample Keyframes [FRAME]"
    description: str = (
        "Picks up to N keyframes per video from the frames currently in scope and "
        "assigns them a tag. Use with a filter to restrict to specific frames."
    )

    @property
    def parameters(self) -> list[BaseParameter]:
        """Return operator parameters."""
        return [
            IntParameter(
                name="max_frames_per_video",
                required=True,
                default=10,
                description="Maximum number of keyframes to select per video.",
            ),
            StringParameter(
                name="tag_name",
                required=True,
                default="keyframe",
                description="Tag assigned to selected keyframes.",
            ),
        ]

    @property
    def supported_scopes(self) -> list[OperatorScope]:
        """Support video-frame scope."""
        return [OperatorScope.VIDEO_FRAME]

    def execute(
        self,
        *,
        session: Session,  # noqa: ARG002
        context: ExecutionContext,
        parameters: dict[str, Any],
    ) -> OperatorResult:
        """Execute the operator."""
        max_frames = parameters.get("max_frames_per_video", 10)
        tag = parameters.get("tag_name", "keyframe")
        scope = "filtered frames" if context.context_filter is not None else "all frames"
        return OperatorResult(
            success=True,
            message=(
                f"Sampled up to {max_frames} keyframes per video from {scope}, "
                f"tagged as '{tag}' in collection {context.collection_id}."
            ),
        )


# ---------------------------------------------------------------------------
# VIDEO — video sub-collections
# Applicable: Videos page (full collection, filtered subset, or single video).
# Not applicable: Samples, Frames, Groups pages.
# ---------------------------------------------------------------------------


@dataclass
class ExtractVideoMetadataOperator(BaseOperator):
    """Read and store duration, frame-rate, and resolution for every video in scope."""

    name: str = "Extract Video Metadata [VIDEO]"
    description: str = (
        "Reads duration, frame-rate, and resolution for every video in scope and "
        "stores the values as sample metadata. Works on the full collection, a filtered "
        "subset, or a single selected video."
    )

    @property
    def parameters(self) -> list[BaseParameter]:
        """Return operator parameters."""
        return [
            BoolParameter(
                name="overwrite_existing",
                required=False,
                default=False,
                description="If true, overwrites metadata that was already extracted.",
            ),
        ]

    @property
    def supported_scopes(self) -> list[OperatorScope]:
        """Support video scope."""
        return [OperatorScope.VIDEO]

    def execute(
        self,
        *,
        session: Session,  # noqa: ARG002
        context: ExecutionContext,
        parameters: dict[str, Any],
    ) -> OperatorResult:
        """Execute the operator."""
        overwrite = parameters.get("overwrite_existing", False)
        scope = "filtered subset" if context.context_filter is not None else "full collection"
        return OperatorResult(
            success=True,
            message=(
                f"Extracted video metadata for {scope} of collection "
                f"{context.collection_id} (overwrite={overwrite})."
            ),
        )


# ---------------------------------------------------------------------------
# GROUP — group items
# Applicable: Groups page.
# Not applicable: Samples, Videos, Frames pages.
# ---------------------------------------------------------------------------


@dataclass
class ValidateGroupCompletenessOperator(BaseOperator):
    """Check that every group in scope has all required component slots filled."""

    name: str = "Validate Group Completeness [GROUP]"
    description: str = (
        "Verifies that every group in scope contains a sample for each defined "
        "component (e.g. photo, scan_upright, clips_video). Incomplete groups are "
        "optionally tagged for review."
    )

    @property
    def parameters(self) -> list[BaseParameter]:
        """Return operator parameters."""
        return [
            BoolParameter(
                name="tag_incomplete",
                required=False,
                default=True,
                description="Tag groups that are missing one or more components.",
            ),
            StringParameter(
                name="tag_name",
                required=False,
                default="incomplete-group",
                description="Tag assigned to incomplete groups (if tag_incomplete is enabled).",
            ),
        ]

    @property
    def supported_scopes(self) -> list[OperatorScope]:
        """Support group scope."""
        return [OperatorScope.GROUP]

    def execute(
        self,
        *,
        session: Session,  # noqa: ARG002
        context: ExecutionContext,
        parameters: dict[str, Any],
    ) -> OperatorResult:
        """Execute the operator."""
        tag_incomplete = parameters.get("tag_incomplete", True)
        tag = parameters.get("tag_name", "incomplete-group")
        action = f"tagging incomplete groups as '{tag}'" if tag_incomplete else "reporting only"
        return OperatorResult(
            success=True,
            message=(
                f"Validated group completeness for collection {context.collection_id} "
                f"({action})."
            ),
        )


# ---------------------------------------------------------------------------
# IMAGE + VIDEO_FRAME — images and frames alike
# Applicable: Samples page AND Frames page.
# Not applicable: Videos, Groups pages.
# ---------------------------------------------------------------------------


@dataclass
class ComputeEmbeddingStatisticsOperator(BaseOperator):
    """Compute per-sample embedding statistics for images and frames in scope."""

    name: str = "Compute Embedding Statistics [IMAGE + FRAME]"
    description: str = (
        "Calculates mean, variance, and nearest-neighbour distance for the embeddings "
        "of every sample in scope. Works on both the Samples page (images) and the "
        "Frames page (video frames)."
    )

    @property
    def parameters(self) -> list[BaseParameter]:
        """Return operator parameters."""
        return [
            IntParameter(
                name="n_neighbors",
                required=False,
                default=5,
                description="Number of nearest neighbours to consider for distance stats.",
            ),
            BoolParameter(
                name="include_metadata",
                required=False,
                default=True,
                description="Store the computed statistics as sample metadata.",
            ),
        ]

    @property
    def supported_scopes(self) -> list[OperatorScope]:
        """Support image and video-frame scopes."""
        return [OperatorScope.IMAGE, OperatorScope.VIDEO_FRAME]

    def execute(
        self,
        *,
        session: Session,  # noqa: ARG002
        context: ExecutionContext,
        parameters: dict[str, Any],
    ) -> OperatorResult:
        """Execute the operator."""
        n_neighbors = parameters.get("n_neighbors", 5)
        include_metadata = parameters.get("include_metadata", True)
        scope = "filtered subset" if context.context_filter is not None else "full collection"
        return OperatorResult(
            success=True,
            message=(
                f"Computed embedding statistics ({n_neighbors} neighbours) for {scope} "
                f"of collection {context.collection_id} "
                f"(metadata={'stored' if include_metadata else 'not stored'})."
            ),
        )


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

# Read environment variables
env = Env()
env.read_env()

# Cleanup an existing database
db_manager.connect(cleanup_existing=True)

# Register all scope-demo operators
operator_registry.register(operator=ExportDatasetManifestOperator())
operator_registry.register(operator=FlagLowQualityImagesOperator())
operator_registry.register(operator=SampleKeyframesOperator())
operator_registry.register(operator=ExtractVideoMetadataOperator())
operator_registry.register(operator=ValidateGroupCompletenessOperator())
operator_registry.register(operator=ComputeEmbeddingStatisticsOperator())

# Define data path
dataset_path = env.path("EXAMPLES_MIDV_PATH", "/path/to/midv/dataset")

# Create a group dataset with IMAGE and VIDEO sub-collections so that each operator
# scope can be exercised from the GUI (Samples → IMAGE, Videos → VIDEO,
# Frames → VIDEO_FRAME, Groups → GROUP, root view → ROOT).
dataset = ls.GroupDataset.create(
    components=[
        ("photo", ls.SampleType.IMAGE),
        ("scan_upright", ls.SampleType.IMAGE),
        ("clips_video", ls.SampleType.VIDEO),
    ]
)

for photo_path in Path(dataset_path / "photo").glob("*.jpg"):
    scan_upright_path = dataset_path / "scan_upright" / photo_path.name
    clips_video_path = dataset_path / "clips_video" / photo_path.with_suffix(".mp4").name

    dataset.add_group_sample(
        components={
            "photo": ls.CreateImage(path=str(photo_path)),
            "scan_upright": ls.CreateImage(path=str(scan_upright_path)),
            "clips_video": ls.CreateVideo(path=str(clips_video_path)),
        }
    )

ls.start_gui()
