"""Implementation of delete function for images."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.resolvers import image_resolver


def delete(session: Session, sample_id: UUID) -> bool:
    """Delete a sample."""
    sample = image_resolver.get_by_id(session=session, sample_id=sample_id)
    if not sample:
        return False

    session.delete(sample)
    session.commit()
    return True
