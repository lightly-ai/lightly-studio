"""Types shared across annotation count resolvers."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID


class AnnotationCountMode(str, Enum):
    """Whether to count annotation objects or distinct annotated samples."""

    OBJECTS = "objects"
    SAMPLES = "samples"


@dataclass
class AnnotationClassCount:
    """Annotation count for one class."""

    label_name: str
    count: int


@dataclass
class SampleTagAnnotationCounts:
    """Annotation class counts for one sample tag."""

    sample_tag_id: UUID
    sample_tag_name: str
    counts: list[AnnotationClassCount] = field(default_factory=list)
