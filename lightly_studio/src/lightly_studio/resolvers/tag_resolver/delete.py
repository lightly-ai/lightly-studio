"""Implementation of delete function for tags."""

from __future__ import annotations

from uuid import UUID

import sqlmodel
from sqlmodel import Session, col

from lightly_studio.models.sample import SampleTagLinkTable
from lightly_studio.resolvers import tag_resolver


def delete(session: Session, tag_id: UUID) -> bool:
    """Delete a tag."""
    tag = tag_resolver.get_by_id(session=session, tag_id=tag_id)
    if not tag:
        return False

    session.exec(
        sqlmodel.delete(SampleTagLinkTable).where(col(SampleTagLinkTable.tag_id) == tag_id)
    )
    session.commit()

    session.delete(tag)
    session.commit()
    return True
