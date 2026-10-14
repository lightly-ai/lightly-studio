"""Helper for updating an annotation field in DuckDB.

DuckDB performs over-eager foreign key checks, which can reject direct UPDATEs on
`annotation_base` when other tables hold FK references to it. We therefore use a
delete-and-reinsert pattern when changing the field association.
See https://duckdb.org/docs/stable/sql/indexes.html#over-eager-constraint-checking-in-foreign-keys

DuckDB has no "looking ahead" functionality for referenced tables and neither does it support
cascading updates. Herefore we need to delete and re-insert the affected rows.
See https://duckdb.org/docs/stable/sql/statements/create_table.html.
"""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
    AnnotationType,
)
from lightly_studio.models.annotation.cuboid_3d import Cuboid3DAnnotationTable, Cuboid3DCreate
from lightly_studio.models.annotation.object_detection import ObjectDetectionAnnotationTable
from lightly_studio.models.annotation.segmentation import SegmentationAnnotationTable
from lightly_studio.models.temporal_span import TemporalSpanTable
from lightly_studio.resolvers import annotation_resolver


def update_annotation_object(
    session: Session,
    annotation: AnnotationBaseTable,
    fields_to_update: dict[str, object] | None,
    cuboid_3d: Cuboid3DCreate | None = None,
) -> AnnotationBaseTable:
    """Update an annotation's field using delete-and-reinsert.

    Args:
        session: Database session for executing the operation.
        annotation: The annotation to update.
        fields_to_update: Dictionary of field names and values to update.
        cuboid_3d: New cuboid geometry to use when reinserting the cuboid row.
            If None, the existing cuboid geometry is preserved.

    Returns:
        A copy of the annotation with the updated fields.
    """
    session.refresh(annotation)
    annotation_copy = annotation.model_copy(update=fields_to_update)

    annotation_type = annotation_copy.annotation_type

    seg_details = annotation_copy.segmentation_details
    segmentation = (
        SegmentationAnnotationTable(
            sample_id=annotation_copy.sample_id,
            segmentation_mask=seg_details.segmentation_mask,
            x=seg_details.x,
            y=seg_details.y,
            width=seg_details.width,
            height=seg_details.height,
        )
        if annotation_type == AnnotationType.SEGMENTATION_MASK and seg_details
        else None
    )

    od_details = annotation_copy.object_detection_details
    object_detection = (
        ObjectDetectionAnnotationTable(
            sample_id=annotation_copy.sample_id,
            x=od_details.x,
            y=od_details.y,
            width=od_details.width,
            height=od_details.height,
        )
        if annotation_type == AnnotationType.OBJECT_DETECTION and od_details
        else None
    )

    cuboid_details = annotation_copy.cuboid_3d_details
    if annotation_type == AnnotationType.CUBOID_3D and cuboid_details:
        source = cuboid_3d if cuboid_3d is not None else cuboid_details
        cuboid = Cuboid3DAnnotationTable(
            sample_id=annotation_copy.sample_id,
            frame_id=source.frame_id,
            px=source.px,
            py=source.py,
            pz=source.pz,
            qx=source.qx,
            qy=source.qy,
            qz=source.qz,
            qw=source.qw,
            sx=source.sx,
            sy=source.sy,
            sz=source.sz,
            interpolated=source.interpolated,
        )
    else:
        cuboid = None

    temporal_span_row = annotation_copy.temporal_span_details
    temporal_span = (
        TemporalSpanTable(
            sample_id=annotation_copy.sample_id,
            start_time_s=temporal_span_row.start_time_s,
            end_time_s=temporal_span_row.end_time_s,
        )
        if temporal_span_row
        else None
    )

    annotation_resolver.delete_annotation(session, annotation.sample_id, delete_sample=False)

    new_annotation = AnnotationBaseTable(
        sample_id=annotation_copy.sample_id,
        annotation_label_id=annotation_copy.annotation_label_id,
        annotation_type=annotation_copy.annotation_type,
        confidence=annotation_copy.confidence,
        created_at=annotation_copy.created_at,
        parent_sample_id=annotation_copy.parent_sample_id,
        object_track_id=annotation_copy.object_track_id,
    )
    session.add(new_annotation)

    if segmentation:
        session.add(segmentation)

    if object_detection:
        session.add(object_detection)

    if cuboid:
        session.add(cuboid)

    if temporal_span:
        session.add(temporal_span)

    session.commit()
    session.flush()

    return annotation_copy
