"""Implementation of split_sample_ids_by_tag function for tags."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select
from sqlmodel.sql.expression import SelectOfScalar

from lightly_studio.models.sample import SampleTagLinkTable


def split_sample_ids_by_tag(
    session: Session,
    tag_id: UUID,
    sample_ids_query: SelectOfScalar[UUID],
) -> tuple[list[UUID], list[UUID]]:
    """Split the samples a query matches into those with and without a tag.

    Callers read this before they add or remove the tag, to know which samples the
    change affects. ``sample_ids_query`` must select a single ``sample_id`` column.

    Returns:
        The matched sample ids with the tag, then the matched sample ids without it.
    """
    matched_ids = list(dict.fromkeys(session.exec(sample_ids_query).all()))
    tagged_ids = set(
        session.exec(
            select(SampleTagLinkTable.sample_id)
            .where(col(SampleTagLinkTable.tag_id) == tag_id)
            .where(col(SampleTagLinkTable.sample_id).in_(sample_ids_query))
        ).all()
    )
    with_tag = [sample_id for sample_id in matched_ids if sample_id in tagged_ids]
    without_tag = [sample_id for sample_id in matched_ids if sample_id not in tagged_ids]
    return with_tag, without_tag
