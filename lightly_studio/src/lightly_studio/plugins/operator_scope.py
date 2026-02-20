"""Scope definitions for operator execution."""

from __future__ import annotations

from enum import Enum
from typing import Final, Literal

from lightly_studio.models.collection import SampleType

ROOT_SAMPLE_TYPE: Final[Literal["ROOT"]] = "ROOT"
CollectionSampleType = SampleType | Literal["ROOT"]


class OperatorScope(str, Enum):
    """Scope in which an operator can be triggered.

    Operators declare which scopes they support via ``BaseOperator.supported_scopes``.
    The UI uses this to surface operators contextually by media type.
    """

    ROOT = "root"
    """Operate on the root collection (dataset-level)."""

    IMAGE = "image"
    """Operate on images and video frames."""

    VIDEO_FRAME = "video_frame"
    """Operate on images and video frames."""

    VIDEO = "video"
    """Operate on the currently selected video."""


SCOPE_TO_SAMPLE_TYPES: dict[OperatorScope, tuple[CollectionSampleType, ...]] = {
    OperatorScope.ROOT: (ROOT_SAMPLE_TYPE,),
    OperatorScope.IMAGE: (SampleType.IMAGE,),
    OperatorScope.VIDEO_FRAME: (SampleType.VIDEO_FRAME,),
    OperatorScope.VIDEO: (SampleType.VIDEO,),
}
"""Hard mapping from operator scope to collection sample type values."""

SAMPLE_TYPE_TO_SCOPE: dict[SampleType, OperatorScope] = {
    SampleType.IMAGE: OperatorScope.IMAGE,
    SampleType.VIDEO_FRAME: OperatorScope.VIDEO_FRAME,
    SampleType.VIDEO: OperatorScope.VIDEO,
}
"""Reverse mapping from collection sample type value to operator scope."""


def get_scope_for_sample_type(sample_type: SampleType) -> OperatorScope:
    """Map a collection sample type to an operator scope."""
    return SAMPLE_TYPE_TO_SCOPE.get(sample_type, OperatorScope.IMAGE)


def get_allowed_scopes_for_collection(
    *, sample_type: SampleType, is_root_collection: bool
) -> list[OperatorScope]:
    """Return the scopes that are valid for a collection context."""
    scopes = [get_scope_for_sample_type(sample_type)]
    if is_root_collection:
        return [OperatorScope.ROOT, *scopes]
    return scopes
