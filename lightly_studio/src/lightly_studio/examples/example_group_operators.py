"""Example of a group dataset with operators for each supported scope."""

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
from lightly_studio.plugins.parameter import BaseParameter
from lightly_studio.resolvers import (
    annotation_resolver,
    collection_resolver,
    group_resolver,
    image_resolver,
    sample_resolver,
    video_frame_resolver,
    video_resolver,
)
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter
from lightly_studio.resolvers.group_resolver.group_filter import GroupFilter
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from lightly_studio.resolvers.video_frame_resolver.video_frame_filter import VideoFrameFilter
from lightly_studio.resolvers.video_resolver.video_filter import VideoFilter


@dataclass
class DemoRootOperator(BaseOperator):
    """Demo operator for the ROOT scope."""

    name: str = "Demo ROOT"
    description: str = "Applicable on root collections."

    @property
    def parameters(self) -> list[BaseParameter]:
        """Return operator parameters."""
        return []

    @property
    def supported_scopes(self) -> list[OperatorScope]:
        """Support root scope."""
        return [OperatorScope.ROOT]

    def execute(
        self,
        session: Session,
        context: ExecutionContext,
        parameters: dict[str, Any],  # noqa: ARG002
    ) -> OperatorResult:
        """Execute the operator."""
        collection = collection_resolver.get_by_id(
            session=session, collection_id=context.collection_id
        )
        sample_type = collection.sample_type.value if collection else "unknown"
        context_filter = context.context_filter
        if isinstance(context_filter, SampleFilter):
            count = sample_resolver.get_filtered_samples(
                session=session, filters=context_filter
            ).total_count
        else:
            count = sample_resolver.count_by_collection_id(
                session=session, collection_id=context.collection_id
            )
        return OperatorResult(
            success=True,
            message=f"ROOT executed on {context.collection_id} (type={sample_type}, n={count}).",
        )


@dataclass
class DemoImageOperator(BaseOperator):
    """Demo operator for the IMAGE scope."""

    name: str = "Demo IMAGE"
    description: str = "Applicable on image collections."

    @property
    def parameters(self) -> list[BaseParameter]:
        """Return operator parameters."""
        return []

    @property
    def supported_scopes(self) -> list[OperatorScope]:
        """Support image scope."""
        return [OperatorScope.IMAGE]

    def execute(
        self,
        session: Session,
        context: ExecutionContext,
        parameters: dict[str, Any],  # noqa: ARG002
    ) -> OperatorResult:
        """Execute the operator."""
        context_filter = context.context_filter
        if isinstance(context_filter, SampleFilter):
            image_filter: ImageFilter | None = ImageFilter(sample_filter=context_filter)
        elif isinstance(context_filter, ImageFilter):
            image_filter = context_filter
        else:
            image_filter = None
        result = image_resolver.get_all_by_collection_id(
            session=session, collection_id=context.collection_id, filters=image_filter
        )
        return OperatorResult(
            success=True,
            message=(
                f"IMAGE executed on {context.collection_id} (type=image, n={result.total_count})."
            ),
        )


@dataclass
class DemoVideoFrameOperator(BaseOperator):
    """Demo operator for the VIDEO_FRAME scope."""

    name: str = "Demo FRAME"
    description: str = "Applicable on video-frame collections."

    @property
    def parameters(self) -> list[BaseParameter]:
        """Return operator parameters."""
        return []

    @property
    def supported_scopes(self) -> list[OperatorScope]:
        """Support video-frame scope."""
        return [OperatorScope.VIDEO_FRAME]

    def execute(
        self,
        session: Session,
        context: ExecutionContext,
        parameters: dict[str, Any],  # noqa: ARG002
    ) -> OperatorResult:
        """Execute the operator."""
        context_filter = context.context_filter
        if isinstance(context_filter, SampleFilter):
            vf_filter: VideoFrameFilter | None = VideoFrameFilter(sample_filter=context_filter)
        elif isinstance(context_filter, VideoFrameFilter):
            vf_filter = context_filter
        else:
            vf_filter = None
        result = video_frame_resolver.get_all_by_collection_id(
            session=session, collection_id=context.collection_id, video_frame_filter=vf_filter
        )
        return OperatorResult(
            success=True,
            message=(
                f"FRAME executed on {context.collection_id} "
                f"(type=video_frame, n={result.total_count})."
            ),
        )


@dataclass
class DemoVideoOperator(BaseOperator):
    """Demo operator for the VIDEO scope."""

    name: str = "Demo VIDEO"
    description: str = "Applicable on video collections."

    @property
    def parameters(self) -> list[BaseParameter]:
        """Return operator parameters."""
        return []

    @property
    def supported_scopes(self) -> list[OperatorScope]:
        """Support video scope."""
        return [OperatorScope.VIDEO]

    def execute(
        self,
        session: Session,
        context: ExecutionContext,
        parameters: dict[str, Any],  # noqa: ARG002
    ) -> OperatorResult:
        """Execute the operator."""
        context_filter = context.context_filter
        if isinstance(context_filter, SampleFilter):
            video_filter: VideoFilter | None = VideoFilter(sample_filter=context_filter)
        elif isinstance(context_filter, VideoFilter):
            video_filter = context_filter
        else:
            video_filter = None
        result = video_resolver.get_all_by_collection_id(
            session=session, collection_id=context.collection_id, filters=video_filter
        )
        return OperatorResult(
            success=True,
            message=(
                f"VIDEO executed on {context.collection_id} (type=video, n={result.total_count})."
            ),
        )


@dataclass
class DemoAnnotationOperator(BaseOperator):
    """Demo operator for the ANNOTATION scope."""

    name: str = "Demo ANNOTATION"
    description: str = "Applicable on annotation collections."

    @property
    def parameters(self) -> list[BaseParameter]:
        """Return operator parameters."""
        return []

    @property
    def supported_scopes(self) -> list[OperatorScope]:
        """Support annotation scope."""
        return [OperatorScope.ANNOTATION]

    def execute(
        self,
        session: Session,
        context: ExecutionContext,
        parameters: dict[str, Any],  # noqa: ARG002
    ) -> OperatorResult:
        """Execute the operator."""
        context_filter = context.context_filter
        if isinstance(context_filter, SampleFilter):
            result = sample_resolver.get_filtered_samples(session=session, filters=context_filter)
            count = result.total_count
        else:
            if isinstance(context_filter, AnnotationsFilter):
                ann_filter = context_filter
            else:
                ann_filter = AnnotationsFilter(collection_ids=[context.collection_id])
            result_anno = annotation_resolver.get_all(session=session, filters=ann_filter)
            count = result_anno.total_count
        return OperatorResult(
            success=True,
            message=(
                f"ANNOTATION executed on {context.collection_id} (type=annotation, n={count})."
            ),
        )


@dataclass
class DemoGroupOperator(BaseOperator):
    """Demo operator for the GROUP scope."""

    name: str = "Demo GROUP"
    description: str = "Applicable on group collections."

    @property
    def parameters(self) -> list[BaseParameter]:
        """Return operator parameters."""
        return []

    @property
    def supported_scopes(self) -> list[OperatorScope]:
        """Support group scope."""
        return [OperatorScope.GROUP]

    def execute(
        self,
        session: Session,
        context: ExecutionContext,
        parameters: dict[str, Any],  # noqa: ARG002
    ) -> OperatorResult:
        """Execute the operator."""
        context_filter = context.context_filter
        if isinstance(context_filter, GroupFilter):
            group_filter = context_filter
        elif isinstance(context_filter, SampleFilter):
            group_filter = GroupFilter(sample_filter=context_filter)
        else:
            group_filter = GroupFilter(
                sample_filter=SampleFilter(collection_id=context.collection_id)
            )
        result = group_resolver.get_all(session=session, pagination=None, filters=group_filter)
        return OperatorResult(
            success=True,
            message=(
                f"GROUP executed on {context.collection_id} (type=group, n={result.total_count})."
            ),
        )


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

env = Env()
env.read_env()

db_manager.connect(cleanup_existing=True)

operator_registry.register(operator=DemoRootOperator())
operator_registry.register(operator=DemoImageOperator())
operator_registry.register(operator=DemoVideoFrameOperator())
operator_registry.register(operator=DemoVideoOperator())
operator_registry.register(operator=DemoAnnotationOperator())
operator_registry.register(operator=DemoGroupOperator())

dataset_path = env.path("EXAMPLES_MIDV_PATH", "/path/to/midv/dataset")

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
