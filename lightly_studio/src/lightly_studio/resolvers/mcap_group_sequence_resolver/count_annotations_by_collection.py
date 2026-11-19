"""Count annotation labels by MCAP sequence collection."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlmodel import Session, asc, col, func, select
from sqlmodel.sql.expression import Select

from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
    AnnotationType,
)
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.mcap_group_sequence import McapGroupSequenceTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.sequence import SampleSequenceLinkTable
from lightly_studio.resolvers import mcap_group_sequence_resolver
from lightly_studio.resolvers.mcap_group_sequence_resolver.mcap_sequence_filter import (
    McapSequenceFilter,
)
from lightly_studio.resolvers.video_resolver.count_video_frame_annotations_by_collection import (
    CountAnnotationsView,
)


def count_annotations_by_collection(
    session: Session,
    collection_id: UUID,
    filters: McapSequenceFilter | None = None,
    annotation_type: AnnotationType | None = None,
) -> list[CountAnnotationsView]:
    """Count the sequences of each annotation label.

    A sequence counts for a label when one of its groups has an annotation with that label.
    The total count includes all sequences of the collection. The current count includes
    only the sequences that match ``filters``. When ``annotation_type`` is set, only
    annotations of that type count.
    """
    mcap_group_sequence_resolver.resolve_embedding_region(
        session=session, collection_id=collection_id, sequence_filter=filters
    )
    label_sequence_pairs = _build_label_sequence_pairs_subquery(
        collection_id=collection_id, annotation_type=annotation_type
    )

    total_query = (
        select(
            label_sequence_pairs.c.label_id,
            func.count(func.distinct(label_sequence_pairs.c.sequence_id)).label("total"),
        )
        .select_from(label_sequence_pairs)
        .group_by(label_sequence_pairs.c.label_id)
        .subquery("total_counts")
    )

    filtered_pairs_query: Select[tuple[Any, Any]] = (
        select(label_sequence_pairs.c.label_id, label_sequence_pairs.c.sequence_id)
        .select_from(label_sequence_pairs)
        .join(
            McapGroupSequenceTable,
            col(McapGroupSequenceTable.sample_id) == label_sequence_pairs.c.sequence_id,
        )
        .join(SampleTable, col(SampleTable.sample_id) == col(McapGroupSequenceTable.sample_id))
    )
    if filters is not None:
        filtered_pairs_query = filters.apply(filtered_pairs_query)
    filtered_pairs = filtered_pairs_query.subquery("filtered_pairs")
    current_query = (
        select(
            filtered_pairs.c.label_id,
            func.count(func.distinct(filtered_pairs.c.sequence_id)).label("current"),
        )
        .select_from(filtered_pairs)
        .group_by(filtered_pairs.c.label_id)
        .subquery("current_counts")
    )

    counts_query: Select[Any] = (
        select(
            col(AnnotationLabelTable.annotation_label_name).label("label"),
            total_query.c.total,
            func.coalesce(current_query.c.current, 0).label("current"),
        )
        .select_from(AnnotationLabelTable)
        .join(total_query, total_query.c.label_id == col(AnnotationLabelTable.annotation_label_id))
        .outerjoin(
            current_query,
            current_query.c.label_id == col(AnnotationLabelTable.annotation_label_id),
        )
        .order_by(asc(AnnotationLabelTable.annotation_label_name))
    )
    rows = session.execute(counts_query).mappings().all()
    return [
        CountAnnotationsView(
            label_name=row["label"], total_count=row["total"], current_count=row["current"]
        )
        for row in rows
    ]


def _build_label_sequence_pairs_subquery(
    collection_id: UUID, annotation_type: AnnotationType | None
) -> Any:
    """Return (label_id, sequence_id) pairs from the annotations of the sequence groups."""
    pairs_query: Select[tuple[Any, Any]] = (
        select(
            col(AnnotationBaseTable.annotation_label_id).label("label_id"),
            col(SampleSequenceLinkTable.sequence_sample_id).label("sequence_id"),
        )
        .select_from(AnnotationBaseTable)
        .join(
            SampleSequenceLinkTable,
            col(SampleSequenceLinkTable.sample_id) == col(AnnotationBaseTable.parent_sample_id),
        )
        .join(
            SampleTable,
            col(SampleTable.sample_id) == col(SampleSequenceLinkTable.sequence_sample_id),
        )
        .where(col(SampleTable.collection_id) == collection_id)
    )
    if annotation_type is not None:
        pairs_query = pairs_query.where(col(AnnotationBaseTable.annotation_type) == annotation_type)
    return pairs_query.subquery("label_sequence_pairs")
