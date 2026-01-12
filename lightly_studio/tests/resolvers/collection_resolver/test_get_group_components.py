from uuid import UUID

import pytest
from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import collection_resolver
from tests.helpers_resolvers import create_collection


def test_get_group_components(db_session: Session) -> None:
    root = create_collection(
        session=db_session,
        collection_name="root",
        sample_type=SampleType.GROUP,
    )
    created_components = collection_resolver.create_group_components(
        session=db_session,
        parent_collection_id=root.collection_id,
        components=[("image", SampleType.IMAGE), ("video", SampleType.VIDEO)],
    )
    # Non-component child collection (should be ignored by get_group_components)
    create_collection(
        session=db_session,
        collection_name="non_component_child",
        sample_type=SampleType.IMAGE,
        parent_collection_id=root.collection_id,
    )

    # Call get_group_components
    components = collection_resolver.get_group_components(
        session=db_session,
        parent_collection_id=root.collection_id,
    )

    assert created_components == components
    assert len(components) == 2
    assert components["image"].group_component_index == 0
    assert components["image"].group_component_name == "image"
    assert components["video"].group_component_index == 1
    assert components["video"].group_component_name == "video"


def test_get_group_components__non_existent_parent(db_session: Session) -> None:
    with pytest.raises(ValueError, match="Parent collection with id .* does not exist."):
        collection_resolver.get_group_components(
            session=db_session,
            parent_collection_id=UUID("00000000-0000-0000-0000-000000000000"),
        )


def test_get_group_components__non_group_parent(db_session: Session) -> None:
    non_group = create_collection(
        session=db_session,
        collection_name="non_group",
        sample_type=SampleType.IMAGE,
    )
    with pytest.raises(
        ValueError, match="Can only get group components for collections of type GROUP."
    ):
        collection_resolver.get_group_components(
            session=db_session,
            parent_collection_id=non_group.collection_id,
        )
