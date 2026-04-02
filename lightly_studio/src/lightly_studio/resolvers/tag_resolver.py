"""Handler for database operations related to tags."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import sqlmodel
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, select

from lightly_studio.models.sample import SampleTable, SampleTagLinkTable
from lightly_studio.models.tag import TagCreate, TagTable, TagUpdate


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


def update(session: Session, tag_id: UUID, tag_data: TagUpdate) -> TagTable | None:
    """Update an existing tag."""
    tag = get_by_id(session=session, tag_id=tag_id)
    if not tag:
        return None

    existing_tag = session.exec(
        select(TagTable).where(
            TagTable.collection_id == tag.collection_id,
            TagTable.kind == tag_data.kind,
            TagTable.name == tag_data.name,
            TagTable.tag_id != tag_id,
        )
    ).one_or_none()
    if existing_tag is not None:
        raise IntegrityError(
            statement="update tag",
            params={"tag_id": tag_id, "name": tag_data.name},
            orig=ValueError("duplicate tag name"),
        )

    linked_sample_ids = list(
        session.exec(
            select(SampleTagLinkTable.sample_id).where(SampleTagLinkTable.tag_id == tag_id)
        ).all()
    )

    if linked_sample_ids:
        session.exec(
            sqlmodel.delete(SampleTagLinkTable).where(col(SampleTagLinkTable.tag_id) == tag_id)
        )
        session.commit()

    try:
        session.exec(
            sqlmodel.update(TagTable)
            .where(TagTable.tag_id == tag_id)
            .values(
                name=tag_data.name,
                description=tag_data.description,
                kind=tag_data.kind,
                updated_at=datetime.now(timezone.utc),
            )
        )
        session.commit()
    except Exception:
        session.rollback()
        for sample_id in linked_sample_ids:
            session.merge(SampleTagLinkTable(sample_id=sample_id, tag_id=tag_id))
        session.commit()
        raise

    for sample_id in linked_sample_ids:
        session.merge(SampleTagLinkTable(sample_id=sample_id, tag_id=tag_id))

    session.commit()
    return get_by_id(session=session, tag_id=tag_id)


def delete(session: Session, tag_id: UUID) -> bool:
    """Delete a tag."""
    tag = get_by_id(session=session, tag_id=tag_id)
    if not tag:
        return False

    session.exec(sqlmodel.delete(SampleTagLinkTable).where(col(SampleTagLinkTable.tag_id) == tag_id))
    session.commit()
    session.exec(sqlmodel.delete(TagTable).where(TagTable.tag_id == tag_id))
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
    """Add a list of sample_ids to a tag."""
    tag = get_by_id(session=session, tag_id=tag_id)
    if not tag or not tag.tag_id:
        return None

    for sample_id in sample_ids:
        session.merge(SampleTagLinkTable(sample_id=sample_id, tag_id=tag_id))

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

    session.exec(
        sqlmodel.delete(SampleTagLinkTable).where(
            col(SampleTagLinkTable.tag_id) == tag_id,
            col(SampleTagLinkTable.sample_id).in_(sample_ids),
        )
    )

    session.commit()
    session.refresh(tag)
    return tag


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
