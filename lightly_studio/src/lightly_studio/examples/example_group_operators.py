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
        _, _ = session, parameters
        return OperatorResult(success=True, message=f"ROOT executed on {context.collection_id}.")


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
        _, _ = session, parameters
        has_filter = context.context_filter is not None
        return OperatorResult(
            success=True,
            message=f"IMAGE executed on {context.collection_id} (filter={has_filter}).",
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
        _, _ = session, parameters
        has_filter = context.context_filter is not None
        return OperatorResult(
            success=True,
            message=f"FRAME executed on {context.collection_id} (filter={has_filter}).",
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
        _, _ = session, parameters
        has_filter = context.context_filter is not None
        return OperatorResult(
            success=True,
            message=f"VIDEO executed on {context.collection_id} (filter={has_filter}).",
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
        _, _ = session, parameters
        return OperatorResult(success=True, message=f"GROUP executed on {context.collection_id}.")


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
        _, _ = session, parameters
        has_filter = context.context_filter is not None
        return OperatorResult(
            success=True,
            message=f"IMAGE+FRAME executed on {context.collection_id} (filter={has_filter}).",
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
