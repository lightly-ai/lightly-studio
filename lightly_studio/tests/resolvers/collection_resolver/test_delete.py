"""Tests for the collection delete resolver function."""

import uuid

from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.models.group_component_definition import GroupComponentDefinitionTable
from lightly_studio.resolvers import collection_resolver
from tests.helpers_resolvers import create_collection


def test_delete(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id  # Capture before delete

    result = collection_resolver.delete(session=db_session, collection_id=collection_id)

    assert result is True
    assert collection_resolver.get_by_id(session=db_session, collection_id=collection_id) is None


def test_delete__non_existent_collection(db_session: Session) -> None:
    result = collection_resolver.delete(session=db_session, collection_id=uuid.uuid4())

    assert result is False


def test_delete__with_group_component_definition(db_session: Session) -> None:
    root = create_collection(session=db_session, sample_type=SampleType.GROUP)
    components = collection_resolver.create_group_components(
        session=db_session,
        parent_collection_id=root.collection_id,
        components=[("front_camera", SampleType.IMAGE)],
    )
    component_collection_id = components["front_camera"].collection_id  # Capture before delete

    result = collection_resolver.delete(session=db_session, collection_id=component_collection_id)

    assert result is True
    assert (
        collection_resolver.get_by_id(session=db_session, collection_id=component_collection_id)
        is None
    )
    assert db_session.get(GroupComponentDefinitionTable, component_collection_id) is None
