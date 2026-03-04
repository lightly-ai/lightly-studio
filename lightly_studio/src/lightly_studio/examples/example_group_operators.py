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
from lightly_studio.resolvers import collection_resolver, sample_resolver
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter


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
        parameters: dict[str, Any],
    ) -> OperatorResult:
        """Execute the operator."""
        _ = parameters
        sample_type, count = _collection_info(session=session, context=context)
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
        parameters: dict[str, Any],
    ) -> OperatorResult:
        """Execute the operator."""
        _ = parameters
        sample_type, count = _collection_info(session=session, context=context)
        return OperatorResult(
            success=True,
            message=f"IMAGE executed on {context.collection_id} (type={sample_type}, n={count}).",
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
        parameters: dict[str, Any],
    ) -> OperatorResult:
        """Execute the operator."""
        _ = parameters
        sample_type, count = _collection_info(session=session, context=context)
        return OperatorResult(
            success=True,
            message=f"FRAME executed on {context.collection_id} (type={sample_type}, n={count}).",
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
        parameters: dict[str, Any],
    ) -> OperatorResult:
        """Execute the operator."""
        _ = parameters
        sample_type, count = _collection_info(session=session, context=context)
        return OperatorResult(
            success=True,
            message=f"VIDEO executed on {context.collection_id} (type={sample_type}, n={count}).",
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
        parameters: dict[str, Any],
    ) -> OperatorResult:
        """Execute the operator."""
        _ = parameters
        sample_type, count = _collection_info(session=session, context=context)
        return OperatorResult(
            success=True,
            message=(
                f"ANNOTATION executed on {context.collection_id} (type={sample_type}, n={count})."
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
        parameters: dict[str, Any],
    ) -> OperatorResult:
        """Execute the operator."""
        _ = parameters
        sample_type, count = _collection_info(session=session, context=context)
        return OperatorResult(
            success=True,
            message=f"GROUP executed on {context.collection_id} (type={sample_type}, n={count}).",
        )


@dataclass
class DemoImageAndFrameOperator(BaseOperator):
    """Demo operator for IMAGE + VIDEO_FRAME scopes."""

    name: str = "Demo IMAGE + FRAME"
    description: str = "Applicable on both image and video-frame collections."

    @property
    def parameters(self) -> list[BaseParameter]:
        """Return operator parameters."""
        return []

    @property
    def supported_scopes(self) -> list[OperatorScope]:
        """Support image and video-frame scopes."""
        return [OperatorScope.IMAGE, OperatorScope.VIDEO_FRAME]

    def execute(
        self,
        session: Session,
        context: ExecutionContext,
        parameters: dict[str, Any],
    ) -> OperatorResult:
        """Execute the operator."""
        _ = parameters
        sample_type, count = _collection_info(session=session, context=context)
        return OperatorResult(
            success=True,
            message=(
                f"IMAGE+FRAME executed on {context.collection_id} (type={sample_type}, n={count})."
            ),
        )


def _collection_info(session: Session, context: ExecutionContext) -> tuple[str, int]:
    """Return (sample_type value, sample count after filter).

    ``context_filter`` may be deserialized as any filter subtype by Pydantic's
    union matching (e.g. AnnotationsFilter instead of SampleFilter when both
    carry ``sample_ids``).  Use ``getattr`` so the count works regardless of
    which concrete type was selected.
    """
    collection = collection_resolver.get_by_id(
        session=session, collection_id=context.collection_id
    )
    sample_type = collection.sample_type.value if collection else "unknown"
    sample_ids = getattr(context.context_filter, "sample_ids", None)
    if sample_ids is not None:
        sf = SampleFilter(collection_id=context.collection_id, sample_ids=sample_ids)
        count = sample_resolver.get_filtered_samples(session=session, filters=sf).total_count
    else:
        count = sample_resolver.count_by_collection_id(
            session=session, collection_id=context.collection_id
        )
    return sample_type, count

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
operator_registry.register(operator=DemoImageAndFrameOperator())

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
