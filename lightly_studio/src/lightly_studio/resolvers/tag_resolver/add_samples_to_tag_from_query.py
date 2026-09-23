"""Implementation of add_samples_to_tag_from_query function for tags."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import literal
from sqlmodel import Session
from sqlmodel.sql.expression import SelectOfScalar

from lightly_studio.database import db_insert
from lightly_studio.models.sample import SampleTagLinkTable
from lightly_studio.models.tag import TagTable
from lightly_studio.resolvers import tag_resolver


def add_samples_to_tag_from_query(
    session: Session,
    tag_id: UUID,
    sample_ids_query: SelectOfScalar[UUID],
) -> TagTable | None:
    """Add every sample matched by ``sample_ids_query`` to a tag.

    Mirrors :func:`add_sample_ids_to_tag_id` but never materializes the ids on the
    client: the matched sample ids are inserted directly via a single server-side
    ``INSERT … SELECT``. ``sample_ids_query`` must select a single ``sample_id``
    column; the constant ``tag_id`` is appended as the second column so the rows
    match ``SampleTagLinkTable``'s ``(sample_id, tag_id)`` shape (``from_select``
    matches columns by position). Idempotent via the composite primary key plus
    conflict handling, so an empty query is a no-op and re-runs add nothing.
    """
    tag = tag_resolver.get_by_id(session=session, tag_id=tag_id)
    if not tag or not tag.tag_id:
        return None

    select_stmt = sample_ids_query.add_columns(literal(tag_id).label("tag_id"))
    db_insert.insert_from_select_ignoring_conflicts(
        session=session,
        table=SampleTagLinkTable,
        columns=["sample_id", "tag_id"],
        select_stmt=select_stmt,
    )

    session.commit()
    session.refresh(tag)
    return tag
