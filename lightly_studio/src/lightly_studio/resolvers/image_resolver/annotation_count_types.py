"""Types for image annotation count resolvers."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from uuid import UUID


class AnnotationCountMode(str, Enum):
    """Controls what the annotation count represents."""

    OBJECTS = "objects"
    SAMPLES = "samples"


@dataclass(frozen=True)
class AnnotationClassCount:
    """Annotation count for one class.

    Attributes:
        label_name: Annotation class name on the shared class axis.
        count: Number of matching annotation objects or distinct annotated samples.
    """

    label_name: str
    count: int


@dataclass(frozen=True)
class SampleTagAnnotationCounts:
    """Annotation class counts for one sample tag.

    Attributes:
        sample_tag_id: ID of the selected sample tag.
        sample_tag_name: Name of the selected sample tag.
        counts: Zero-filled counts on the shared class axis.
    """

    sample_tag_id: UUID
    sample_tag_name: str
    counts: tuple[AnnotationClassCount, ...]


@dataclass(frozen=True)
class AnnotationPairCount:
    """Annotation count for one (annotation source, annotation class) pair.

    Attributes:
        annotation_collection_id: ID of the annotation source collection.
        annotation_label_id: ID of the annotation class.
        label_name: Name of the annotation class.
        current_count: Count with the filter applied.
        total_count: Count without the filter.
    """

    annotation_collection_id: UUID
    annotation_label_id: UUID
    label_name: str
    current_count: int
    total_count: int
