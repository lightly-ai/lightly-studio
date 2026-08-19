"""Implementation of rename function for tags."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import sqlmodel
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, select

from lightly_studio.models.sample import SampleTagLinkTable
from lightly_studio.models.tag import TagTable
from lightly_studio.resolvers import tag_resolver


def rename(session: Session, tag_id: UUID, new_name: str) -> TagTable | None:
    """Rename an existing tag."""
    tag = tag_resolver.get_by_id(session=session, tag_id=tag_id)
    if not tag:
        return None

    conflicting_tag = tag_resolver.get_by_name(
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

    tag = tag_resolver.get_by_id(session=session, tag_id=tag_id)
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
