"""Handler for database operations related to tags."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import sqlmodel
from sqlmodel import Session, col, select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.annotation.links import AnnotationTagLinkTable
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

    # due to duckdb/OLAP optimisations, update operations effecting unique
    # constraints (e.g colums) will lead to a unique constraint violation.
    # This is due to a update is implemented as delete+insert. The error
    # happens only within the same session.
    # To fix it, we can delete, commit + insert a new tag.
    # https://duckdb.org/docs/sql/indexes#over-eager-unique-constraint-checking
    session.delete(tag)
    session.commit()

    # create clone of tag with updated values
    tag_updated = TagTable.model_validate(tag)
    tag_updated.name = tag_data.name
    tag_updated.description = tag_data.description
    tag_updated.updated_at = datetime.now(timezone.utc)

    session.add(tag_updated)
    session.commit()
    session.refresh(tag_updated)
    return tag_updated


def delete(session: Session, tag_id: UUID) -> bool:
    """Delete a tag."""
    tag = get_by_id(session=session, tag_id=tag_id)
    if not tag:
        return False

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
    if tag.kind != "sample":
        raise ValueError(f"Tag {tag_id} is not of kind 'sample'")

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
    if tag.kind != "sample":
        raise ValueError(f"Tag {tag_id} is not of kind 'sample'")

    sample.tags.remove(tag)
    session.add(sample)
    session.commit()
    session.refresh(sample)
    return sample


def add_tag_to_annotation(
    session: Session,
    tag_id: UUID,
    annotation: AnnotationBaseTable,
) -> AnnotationBaseTable | None:
    """Add a tag to a annotation."""
    tag = get_by_id(session=session, tag_id=tag_id)
    if not tag or not tag.tag_id:
        return None
    if tag.kind != "annotation":
        raise ValueError(f"Tag {tag_id} is not of kind 'annotation'")

    annotation.tags.append(tag)
    session.add(annotation)
    session.commit()
    session.refresh(annotation)
    return annotation


def assign_tag_to_annotation(
    session: Session,
    tag: TagTable,
    annotation: AnnotationBaseTable,
) -> AnnotationBaseTable:
    """Add a tag to a annotation."""
    annotation.tags.append(tag)
    session.add(annotation)
    session.commit()
    session.refresh(annotation)
    return annotation


def remove_tag_from_annotation(
    session: Session,
    tag_id: UUID,
    annotation: AnnotationBaseTable,
) -> AnnotationBaseTable | None:
    """Remove a tag from a annotation."""
    tag = get_by_id(session=session, tag_id=tag_id)
    if not tag or not tag.tag_id:
        return None
    if tag.kind != "annotation":
        raise ValueError(f"Tag {tag_id} is not of kind 'annotation'")

    annotation.tags.remove(tag)
    session.add(annotation)
    session.commit()
    session.refresh(annotation)
    return annotation


def add_sample_ids_to_tag_id(
    session: Session,
    tag_id: UUID,
    sample_ids: list[UUID],
) -> TagTable | None:
    """Add a list of sample_ids to a tag."""
    tag = get_by_id(session=session, tag_id=tag_id)
    if not tag or not tag.tag_id:
        return None
    if tag.kind != "sample":
        raise ValueError(f"Tag {tag_id} is not of kind 'sample'")

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
    if tag.kind != "sample":
        raise ValueError(f"Tag {tag_id} is not of kind 'sample'")

    session.exec(  # type:ignore[call-overload]
        sqlmodel.delete(SampleTagLinkTable).where(
            col(SampleTagLinkTable.tag_id) == tag_id,
            col(SampleTagLinkTable.sample_id).in_(sample_ids),
        )
    )

    session.commit()
    session.refresh(tag)
    return tag


def add_annotation_ids_to_tag_id(
    session: Session,
    tag_id: UUID,
    annotation_ids: list[UUID],
) -> TagTable | None:
    """Add a list of annotation_ids to a tag."""
    tag = get_by_id(session=session, tag_id=tag_id)
    if not tag or not tag.tag_id:
        return None
    if tag.kind != "annotation":
        raise ValueError(f"Tag {tag_id} is not of kind 'annotation'")

    for annotation_id in annotation_ids:
        session.merge(
            AnnotationTagLinkTable(
                tag_id=tag_id,
                annotation_sample_id=annotation_id,
            )
        )

    session.commit()
    session.refresh(tag)
    return tag


def remove_annotation_ids_from_tag_id(
    session: Session,
    tag_id: UUID,
    annotation_ids: list[UUID],
) -> TagTable | None:
    """Remove a list of things to a tag."""
    tag = get_by_id(session=session, tag_id=tag_id)
    if not tag or not tag.tag_id:
        return None
    if tag.kind != "annotation":
        raise ValueError(f"Tag {tag_id} is not of kind 'annotation'")

    session.exec(  # type:ignore[call-overload]
        sqlmodel.delete(AnnotationTagLinkTable).where(
            col(AnnotationTagLinkTable.tag_id) == tag_id,
            col(AnnotationTagLinkTable.annotation_sample_id).in_(annotation_ids),
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
