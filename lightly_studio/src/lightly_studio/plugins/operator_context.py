"""Scope definitions for operator execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Annotated, Protocol, Union
from uuid import UUID

from pydantic import Field

from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter
from lightly_studio.resolvers.group_resolver.group_filter import GroupFilter
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from lightly_studio.resolvers.video_frame_resolver.video_frame_filter import VideoFrameFilter
from lightly_studio.resolvers.video_resolver.video_filter import VideoFilter

# Discriminated union: each member carries a unique ``filter_type`` literal so a
# payload resolves to exactly one model by intent, not by structural fit. A plain
# ``Union`` resolves overlapping payloads by declaration order — e.g. a bare
# ``{"sample_ids": [...]}`` fits both SampleFilter and AnnotationsFilter, and the
# first-listed member silently wins. The discriminator removes that ambiguity, so
# every payload MUST include ``filter_type``.
AnyFilter = Annotated[
    Union[
        ImageFilter,
        VideoFrameFilter,
        VideoFilter,
        AnnotationsFilter,
        GroupFilter,
        SampleFilter,
    ],
    Field(discriminator="filter_type"),
]


class ProgressReporter(Protocol):
    """Callback an operator uses to report how far along its run is."""

    def __call__(self, *, current: int, total: int, description: str = "") -> None:
        """Report progress of the current run.

        Args:
            current: Number of units processed so far.
            total: Total number of units to process.
            description: Human-readable description of the current step.
        """


# Defined above ExecutionContext because a dataclass field default is evaluated
# when the class body runs, so it cannot live with the other private helpers at
# the bottom of the file.
def _report_progress_noop(*, current: int, total: int, description: str = "") -> None:
    """Discard reported progress. Default for runs that report nowhere."""


@dataclass
class ExecutionContext:
    """Contextual data passed to ``BaseOperator.execute()``.

    ``filter=None`` means the whole collection, while a non-null filter
    restricts the target samples.
    """

    collection_id: UUID
    context_filter: AnyFilter | None = None

    report_progress: ProgressReporter = field(default=_report_progress_noop)
    """Reports run progress to the UI.

    Operators should call this from their sample loop, e.g.
    ``context.report_progress(current=i, total=len(samples), description="Running inference")``.
    Defaults to a no-op, so operators that do not report progress keep working
    unchanged and the UI falls back to an indeterminate spinner.
    """


class OperatorScope(str, Enum):
    """Scope in which an operator can be triggered.

    Operators declare which scopes they support via ``BaseOperator.supported_scopes``.
    The UI uses this to surface operators contextually by media type.
    """

    ROOT = "root"
    """Operate on the root collection (dataset-level)."""

    IMAGE = "image"
    """Operate on images."""

    VIDEO_FRAME = "video_frame"
    """Operate on video frames."""

    VIDEO = "video"
    """Operate on videos."""

    ANNOTATION = "annotation"
    """Operate on annotations."""

    GROUP = "group"
    """Operate on groups."""

    CAPTION = "caption"
    """Operate on captions."""


def get_allowed_scopes_for_collection(
    sample_type: SampleType, is_root_collection: bool
) -> list[OperatorScope]:
    """Return the scopes that are valid for a collection context."""
    scope = OperatorScope(sample_type.value)
    if is_root_collection:
        return [OperatorScope.ROOT, scope]
    return [scope]
