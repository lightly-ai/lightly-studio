"""Implementation of get_cuboid_frame_ids_by_sequence_ids for annotation resolver."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlmodel import Session, col, func, select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable, AnnotationType
from lightly_studio.models.annotation.cuboid_3d import Cuboid3DAnnotationTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.sequence import SampleSequenceLinkTable


def get_cuboid_frame_ids_by_sequence_ids(
    session: Session, sequence_ids: Sequence[UUID], annotation_collection_id: UUID
) -> list[str]:
    """Returns the frames the cuboids of the sequences' ticks are stored in.

    Args:
        session: The database session.
        sequence_ids: The sequences whose ticks are searched. An empty sequence gives `[]`.
        annotation_collection_id: The annotation source to count the cuboids of.

    Returns:
        The frame IDs, ordered by cuboid count descending, then by name. Empty frame IDs
        are left out.
    """
    if not sequence_ids:
        return []
    cuboid_count = func.count(col(Cuboid3DAnnotationTable.sample_id))
    statement = (
        select(col(Cuboid3DAnnotationTable.frame_id), cuboid_count)
        .join(
            AnnotationBaseTable,
            col(AnnotationBaseTable.sample_id) == col(Cuboid3DAnnotationTable.sample_id),
        )
        .join(SampleTable, col(SampleTable.sample_id) == col(AnnotationBaseTable.sample_id))
        .join(
            SampleSequenceLinkTable,
            col(SampleSequenceLinkTable.sample_id) == col(AnnotationBaseTable.parent_sample_id),
        )
        .where(col(SampleSequenceLinkTable.sequence_sample_id).in_(sequence_ids))
        .where(col(SampleTable.collection_id) == annotation_collection_id)
        .where(col(AnnotationBaseTable.annotation_type) == AnnotationType.CUBOID_3D)
        .where(col(Cuboid3DAnnotationTable.frame_id) != "")
        .group_by(col(Cuboid3DAnnotationTable.frame_id))
        .order_by(cuboid_count.desc(), col(Cuboid3DAnnotationTable.frame_id))
    )
    return [frame_id for frame_id, _ in session.exec(statement).all()]
