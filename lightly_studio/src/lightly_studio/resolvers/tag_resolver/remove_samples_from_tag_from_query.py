"""Implementation of remove_samples_from_tag_from_query function for tags."""

from __future__ import annotations

from uuid import UUID

import sqlmodel
from sqlmodel import Session, col, select
from sqlmodel.sql.expression import SelectOfScalar

from lightly_studio.models.sample import SampleTagLinkTable
from lightly_studio.models.tag import TagTable
from lightly_studio.resolvers import tag_resolver


def remove_samples_from_tag_from_query(
    session: Session,
    tag_id: UUID,
    sample_ids_query: SelectOfScalar[UUID],
) -> TagTable | None:
    """Remove every sample matched by ``sample_ids_query`` from a tag.

    Mirrors :func:`add_samples_to_tag_from_query`. ``sample_ids_query`` must select a
    single ``sample_id`` column. Samples without the tag are ignored.
    """
    tag = tag_resolver.get_by_id(session=session, tag_id=tag_id)
    if not tag or not tag.tag_id:
        return None

    sample_ids_subquery = sample_ids_query.subquery()
    session.exec(
        sqlmodel.delete(SampleTagLinkTable).where(
            col(SampleTagLinkTable.tag_id) == tag_id,
            col(SampleTagLinkTable.sample_id).in_(select(sample_ids_subquery.c[0])),
        )
    )

    session.commit()
    session.refresh(tag)
    return tag
