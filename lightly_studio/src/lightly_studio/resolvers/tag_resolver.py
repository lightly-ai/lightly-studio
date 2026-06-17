"""Handler for database operations related to tags."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone
from uuid import UUID

import sqlmodel
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, func, select

from lightly_studio.database import db_array, db_insert
from lightly_studio.models.sample import SampleTable, SampleTagLinkTable
from lightly_studio.models.tag import TagCreate, TagTable
from lightly_studio.utils import batching


def create(session: Session, tag: TagCreate) -> TagTable:
    """Create a new tag in the database."""
    db_tag = TagTable.model_validate(tag)
    session.add(db_tag)
    session.commit()
    session.refresh(db_tag)
    return db_tag


# TODO(Michal, 06/2025): Use Paginated struct instead of offset/limit.
def get_all_by_collection_id(
    session: Session, collection_id: UUID, offset: int = 0, limit: int | None = None
) -> list[TagTable]:
    """Retrieve all tags with pagination."""
    query = (
        select(TagTable)
        .where(TagTable.collection_id == collection_id)
        .order_by(col(TagTable.created_at).asc(), col(TagTable.tag_id).asc())
        .offset(offset)
    )
    if limit is not None:
        query = query.limit(limit)
    tags = session.exec(query).all()
    return list(tags) if tags else []


def get_by_id(session: Session, tag_id: UUID) -> TagTable | None:
    """Retrieve a single tag by ID."""
    return session.exec(select(TagTable).where(TagTable.tag_id == tag_id)).one_or_none()


def get_by_name(session: Session, tag_name: str, collection_id: UUID | None) -> TagTable | None:
    """Retrieve a single tag by ID."""
    if collection_id:
        return session.exec(
            select(TagTable)
            .where(TagTable.collection_id == collection_id)
            .where(TagTable.name == tag_name)
        ).one_or_none()
    return session.exec(select(TagTable).where(TagTable.name == tag_name)).one_or_none()


def rename(session: Session, tag_id: UUID, new_name: str) -> TagTable | None:
    """Rename an existing tag."""
    tag = get_by_id(session=session, tag_id=tag_id)
    if not tag:
        return None

    conflicting_tag = get_by_name(
        session=session, tag_name=new_name, collection_id=tag.collection_id
    )
    if conflicting_tag and conflicting_tag.tag_id != tag_id and conflicting_tag.kind == tag.kind:
        raise IntegrityError(statement=None, params=None, orig=Exception("Tag already exists"))

    if new_name == tag.name:
        return tag

    sample_ids = [
        sample_id
        for sample_id in session.exec(
            select(SampleTagLinkTable.sample_id).where(col(SampleTagLinkTable.tag_id) == tag_id)
        ).all()
        if sample_id is not None
    ]

    # DuckDB rejects updates and deletes of referenced rows in the same transaction.
    # Commit each step so renaming a tag preserves existing sample links.
    session.exec(
        sqlmodel.delete(SampleTagLinkTable).where(col(SampleTagLinkTable.tag_id) == tag_id)
    )
    session.commit()

    tag = get_by_id(session=session, tag_id=tag_id)
    if not tag:
        return None

    session.delete(tag)
    session.commit()

    tag_renamed = TagTable(
        tag_id=tag_id,
        collection_id=tag.collection_id,
        name=new_name,
        kind=tag.kind,
        created_at=tag.created_at,
        updated_at=datetime.now(timezone.utc),
    )
    session.add(tag_renamed)
    session.commit()

    if sample_ids:
        session.add_all(
            [SampleTagLinkTable(sample_id=sample_id, tag_id=tag_id) for sample_id in sample_ids]
        )
        session.commit()

    session.refresh(tag_renamed)
    return tag_renamed


def delete(session: Session, tag_id: UUID) -> bool:
    """Delete a tag."""
    tag = get_by_id(session=session, tag_id=tag_id)
    if not tag:
        return False

    session.exec(
        sqlmodel.delete(SampleTagLinkTable).where(col(SampleTagLinkTable.tag_id) == tag_id)
    )
    session.commit()

    session.delete(tag)
    session.commit()
    return True


def add_tag_to_sample(
    session: Session,
    tag_id: UUID,
    sample: SampleTable,
) -> SampleTable | None:
    """Add a tag to a sample."""
    tag = get_by_id(session=session, tag_id=tag_id)
    if not tag or not tag.tag_id:
        return None

    sample.tags.append(tag)
    session.add(sample)
    session.commit()
    session.refresh(sample)
    return sample


def remove_tag_from_sample(
    session: Session,
    tag_id: UUID,
    sample: SampleTable,
) -> SampleTable | None:
    """Remove a tag from a sample."""
    tag = get_by_id(session=session, tag_id=tag_id)
    if not tag or not tag.tag_id:
        return None

    sample.tags.remove(tag)
    session.add(sample)
    session.commit()
    session.refresh(sample)
    return sample


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
    """
    tag = get_by_id(session=session, tag_id=tag_id)
    if not tag or not tag.tag_id:
        return None

    rows = [{"sample_id": sample_id, "tag_id": tag_id} for sample_id in set(sample_ids)]
    db_insert.insert_ignoring_conflicts(session=session, table=SampleTagLinkTable, rows=rows)

    session.commit()
    session.refresh(tag)
    return tag


def remove_sample_ids_from_tag_id(
    session: Session,
    tag_id: UUID,
    sample_ids: list[UUID],
) -> TagTable | None:
    """Remove a list of sample_ids to a tag."""
    tag = get_by_id(session=session, tag_id=tag_id)
    if not tag or not tag.tag_id:
        return None

    for batch in batching.batched(items=sample_ids):
        session.exec(
            sqlmodel.delete(SampleTagLinkTable).where(
                col(SampleTagLinkTable.tag_id) == tag_id,
                col(SampleTagLinkTable.sample_id).in_(batch),
            )
        )

    session.commit()
    session.refresh(tag)
    return tag


def get_names_by_ids(session: Session, tag_ids: Sequence[UUID]) -> dict[UUID, str]:
    """Return ``{tag_id: name}`` for the requested tags."""
    if not tag_ids:
        return {}
    stmt = select(TagTable.tag_id, TagTable.name).where(
        db_array.in_array(column=col(TagTable.tag_id), values=tag_ids)
    )
    return dict(session.exec(stmt).all())


def get_tags_by_sample(
    session: Session,
    tag_ids: Sequence[UUID],
) -> dict[UUID, set[UUID]]:
    """Return ``{sample_id: {tag_id, ...}}`` for the requested tags."""
    if not tag_ids:
        return {}
    stmt = select(SampleTagLinkTable.sample_id, SampleTagLinkTable.tag_id).where(
        db_array.in_array(column=col(SampleTagLinkTable.tag_id), values=tag_ids)
    )
    result: dict[UUID, set[UUID]] = {}
    for sample_id, tag_id in session.exec(stmt).all():
        assert sample_id is not None
        assert tag_id is not None
        result.setdefault(sample_id, set()).add(tag_id)
    return result


def get_or_create_sample_tag_by_name(
    session: Session,
    collection_id: UUID,
    tag_name: str,
) -> TagTable:
    """Get an existing sample tag by name or create a new one if it doesn't exist.

    Args:
        session: Database session for executing queries.
        collection_id: The collection ID to search/create the tag for.
        tag_name: Name of the tag to get or create.

    Returns:
        The existing or newly created sample tag.
    """
    existing_tag = get_by_name(session=session, tag_name=tag_name, collection_id=collection_id)
    if existing_tag:
        return existing_tag

    new_tag = TagCreate(name=tag_name, collection_id=collection_id, kind="sample")
    return create(session=session, tag=new_tag)


def get_most_used_by_collection_id(
    session: Session,
    collection_id: UUID,
    limit: int = 30,
) -> dict[UUID, str]:
    """Return the most used tags in a collection.

    Tags are ordered by descending number of sample assignments. Ties are
    resolved deterministically by creation time and tag ID.

    Args:
        session: Database session for executing queries.
        collection_id: The collection whose tags should be returned.
        limit: Maximum number of tags to return.

    Returns:
        A mapping of tag ID to tag name for the most used tags in the collection.
    """
    usage_count = func.count(col(SampleTagLinkTable.sample_id))
    query = (
        select(TagTable.tag_id, TagTable.name, usage_count)
        .where(TagTable.collection_id == collection_id)
        .outerjoin(SampleTagLinkTable, col(SampleTagLinkTable.tag_id) == col(TagTable.tag_id))
        .group_by(
            col(TagTable.tag_id),
            col(TagTable.name),
            col(TagTable.created_at),
        )
        .order_by(
            usage_count.desc(),
            col(TagTable.created_at).asc(),
            col(TagTable.tag_id).asc(),
        )
        .limit(limit)
    )
    return {tag_id: tag_name for tag_id, tag_name, _ in session.exec(query).all()}
