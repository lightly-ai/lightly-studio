"""Implementation of add_sample_ids_to_tag_id function for tags."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.database import db_array, db_insert
from lightly_studio.models.sample import SampleTable, SampleTagLinkTable
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
    deduplicated, so links are never created twice. Uses a batched bulk INSERT
    (one statement per batch) instead of one round-trip per sample id.

    Raises:
        ValueError: If a sample is not in the collection of the tag.
    """
    tag = tag_resolver.get_by_id(session=session, tag_id=tag_id)
    if not tag or not tag.tag_id:
        return None
    if sample_ids:
        _check_samples_in_collection(session=session, tag=tag, sample_ids=sample_ids)

    rows = [{"sample_id": sample_id, "tag_id": tag_id} for sample_id in set(sample_ids)]
    db_insert.insert_ignoring_conflicts(session=session, table=SampleTagLinkTable, rows=rows)

    session.commit()
    session.refresh(tag)
    return tag


def _check_samples_in_collection(session: Session, tag: TagTable, sample_ids: list[UUID]) -> None:
    other_sample_ids = session.exec(
        select(SampleTable.sample_id)
        .where(db_array.in_array(column=col(SampleTable.sample_id), values=sample_ids))
        .where(SampleTable.collection_id != tag.collection_id)
        .limit(5)
    ).all()
    if other_sample_ids:
        raise ValueError(
            f"Samples {list(other_sample_ids)} do not belong to the collection of tag '{tag.name}'."
        )
