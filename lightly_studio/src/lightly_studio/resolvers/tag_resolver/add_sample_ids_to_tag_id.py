"""Implementation of add_sample_ids_to_tag_id function for tags."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, func, select
from sqlmodel.sql.expression import SelectOfScalar

from lightly_studio.database import db_array
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.tag import TagTable
from lightly_studio.resolvers import tag_resolver


def add_sample_ids_to_tag_id(
    session: Session,
    tag_id: UUID,
    sample_ids: list[UUID],
) -> TagTable | None:
    """Add a list of sample_ids to a tag.

    Idempotent: sample ids that are already linked to the tag are skipped via
    database-level conflict handling, and duplicate sample ids in the input are
    deduplicated, so links are never created twice. Inserts all links with one
    INSERT ... SELECT, so the database builds the rows and Python sends only the ids.

    Raises:
        ValueError: If a sample does not exist or is not in the collection of the tag.
    """
    tag = tag_resolver.get_by_id(session=session, tag_id=tag_id)
    if not tag or not tag.tag_id:
        return None
    if not sample_ids:
        return tag

    sample_ids_query = (
        select(SampleTable.sample_id)
        .where(db_array.in_array(column=col(SampleTable.sample_id), values=sample_ids))
        .where(col(SampleTable.collection_id) == tag.collection_id)
    )
    _check_samples_in_collection(
        session=session, tag=tag, sample_ids=sample_ids, query=sample_ids_query
    )
    return tag_resolver.add_samples_to_tag_from_query(
        session=session, tag_id=tag_id, sample_ids_query=sample_ids_query
    )


def _check_samples_in_collection(
    session: Session,
    tag: TagTable,
    sample_ids: list[UUID],
    query: SelectOfScalar[UUID],
) -> None:
    """Raise if the query does not return every sample id, ignoring duplicates."""
    unique_sample_ids = set(sample_ids)
    matched_count = session.exec(select(func.count()).select_from(query.subquery())).one()
    if matched_count == len(unique_sample_ids):
        return

    unmatched_sample_ids = unique_sample_ids - set(session.exec(query).all())
    raise ValueError(
        f"Samples {list(unmatched_sample_ids)[:5]} do not exist or do not belong to the "
        f"collection of tag '{tag.name}'."
    )
