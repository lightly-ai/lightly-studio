"""Implementation of count_samples_per_tag function for tags."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, func, select
from sqlmodel.sql.expression import SelectOfScalar

from lightly_studio.models.sample import SampleTagLinkTable
from lightly_studio.models.tag import TagTable


def count_samples_per_tag(
    session: Session,
    collection_id: UUID,
    sample_ids_query: SelectOfScalar[UUID],
) -> dict[UUID, int]:
    """Count, for each tag of a collection, how many samples of the query carry it.

    Tags that none of the samples carry are omitted.
    """
    rows = session.exec(
        select(TagTable.tag_id, func.count(col(SampleTagLinkTable.sample_id)))
        .join(SampleTagLinkTable, col(SampleTagLinkTable.tag_id) == col(TagTable.tag_id))
        .where(
            col(TagTable.collection_id) == collection_id,
            col(SampleTagLinkTable.sample_id).in_(sample_ids_query),
        )
        .group_by(col(TagTable.tag_id))
    ).all()
    return dict(rows)
