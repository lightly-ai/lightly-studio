"""Load annotation data for the samples selected for export."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Iterator, Sequence
from typing import TypeVar
from uuid import UUID

from sqlalchemy.orm import joinedload, lazyload
from sqlalchemy.orm.interfaces import LoaderOption
from sqlmodel import Session, col, select

from lightly_studio.core.sample import Sample
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable, AnnotationType
from lightly_studio.models.sample import SampleTable
from lightly_studio.utils import batching

_Sample = TypeVar("_Sample", bound=Sample)

# Bound the number of samples whose annotation payloads are loaded at once.
_EXPORT_BATCH_SIZE = 500


def iter_sample_annotations(
    session: Session,
    samples: Iterable[_Sample],
    annotation_types: Sequence[AnnotationType],
    annotation_collection_id: UUID | None,
) -> Iterator[tuple[_Sample, list[AnnotationBaseTable]]]:
    """Yield samples in input order with the annotations needed by the export."""
    query = (
        select(AnnotationBaseTable)
        .where(col(AnnotationBaseTable.annotation_type).in_(annotation_types))
        # Pascal VOC writes overlapping pixels in annotation order.
        .order_by(col(AnnotationBaseTable.created_at), col(AnnotationBaseTable.sample_id))
        .options(lazyload(AnnotationBaseTable.object_track), *_export_options(annotation_types))
    )
    if annotation_collection_id is not None:
        query = query.where(
            AnnotationBaseTable.sample.has(
                col(SampleTable.collection_id) == annotation_collection_id
            )
        )

    for batch in batching.batched(items=samples, batch_size=_EXPORT_BATCH_SIZE):
        sample_ids = {sample.sample_id for sample in batch}
        annotations_by_sample_id: dict[UUID, list[AnnotationBaseTable]] = defaultdict(list)
        batch_query = query.where(col(AnnotationBaseTable.parent_sample_id).in_(sample_ids))
        for annotation in session.exec(batch_query):
            annotations_by_sample_id[annotation.parent_sample_id].append(annotation)
        for sample in batch:
            yield sample, annotations_by_sample_id.get(sample.sample_id, [])


def _export_options(annotation_types: Sequence[AnnotationType]) -> list[LoaderOption]:
    if AnnotationType.CLASSIFICATION in annotation_types:
        # CSV uses the source name and excludes classifications with a temporal span.
        return [
            joinedload(AnnotationBaseTable.annotation_label),
            joinedload(AnnotationBaseTable.sample).joinedload(SampleTable.collection),
            joinedload(AnnotationBaseTable.temporal_span_details),
        ]
    shape_options: list[LoaderOption] = []
    if AnnotationType.OBJECT_DETECTION in annotation_types:
        shape_options.append(joinedload(AnnotationBaseTable.object_detection_details))
    if AnnotationType.SEGMENTATION_MASK in annotation_types:
        shape_options.append(joinedload(AnnotationBaseTable.segmentation_details))
    if AnnotationType.POLYGON in annotation_types:
        shape_options.append(joinedload(AnnotationBaseTable.polygon_details))
    return [*shape_options, lazyload(AnnotationBaseTable.temporal_span_details)]
