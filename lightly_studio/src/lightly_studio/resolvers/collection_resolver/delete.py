"""Implementation of delete collection resolver function."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import collection_resolver
from lightly_studio.resolvers.collection_resolver import delete_annotation_source


def delete(session: Session, collection_id: UUID) -> bool:
    """Delete a collection."""
    collection = collection_resolver.get_by_id(session=session, collection_id=collection_id)
    if not collection:
        return False

    if collection.sample_type == SampleType.ANNOTATION:
        delete_annotation_source.delete_annotation_source(session=session, collection=collection)
        return True

    if collection.group_component_definition is not None:
        session.delete(collection.group_component_definition)
        collection.group_component_definition = None
        session.commit()

    session.delete(collection)
    session.commit()
    return True
