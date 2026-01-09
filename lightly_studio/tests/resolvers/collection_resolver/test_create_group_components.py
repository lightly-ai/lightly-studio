from uuid import UUID

import pytest
from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import collection_resolver
from tests.helpers_resolvers import create_collection


def test_create_group_components(db_session: Session) -> None:
    root = create_collection(
        session=db_session,
        collection_name="root",
        sample_type=SampleType.GROUP,
    )
    components = collection_resolver.create_group_components(
        session=db_session,
        parent_collection_id=root.collection_id,
        components=[("image", SampleType.IMAGE), ("video", SampleType.VIDEO)],
    )

    assert len(root.children) == 2
    assert len(components) == 2
    assert {root.children[0].collection_id, root.children[1].collection_id} == {
        components["image"].collection_id,
        components["video"].collection_id,
    }

    assert components["image"].group_component_index == 0
    assert components["image"].group_component_name == "image"
    assert components["image"].sample_type == SampleType.IMAGE
    assert components["image"].name == "root_comp_0"

    assert components["video"].group_component_index == 1
    assert components["video"].group_component_name == "video"
    assert components["video"].sample_type == SampleType.VIDEO
    assert components["video"].name == "root_comp_1"


def test_create_group_components__non_existent_parent(db_session: Session) -> None:
    with pytest.raises(ValueError, match="Parent collection with id .* does not exist."):
        collection_resolver.create_group_components(
            session=db_session,
            parent_collection_id=UUID("00000000-0000-0000-0000-000000000000"),
            components=[],
        )


def test_create_group_components__non_group_parent(db_session: Session) -> None:
    non_group = create_collection(
        session=db_session,
        collection_name="non_group",
        sample_type=SampleType.IMAGE,
    )
    with pytest.raises(
        ValueError, match="Can only create group components for collections of type GROUP."
    ):
        collection_resolver.create_group_components(
            session=db_session,
            parent_collection_id=non_group.collection_id,
            components=[],
        )


def test_create_group_components__existing_components(db_session: Session) -> None:
    group = create_collection(
        session=db_session,
        collection_name="group",
        sample_type=SampleType.GROUP,
    )
    collection_resolver.create_group_components(
        session=db_session,
        parent_collection_id=group.collection_id,
        components=[("comp1", SampleType.IMAGE)],
    )
    with pytest.raises(
        ValueError, match="Group components already exist for this parent collection."
    ):
        collection_resolver.create_group_components(
            session=db_session,
            parent_collection_id=group.collection_id,
            components=[("comp2", SampleType.VIDEO)],
        )


def test_create_group_components__duplicate_component_names(db_session: Session) -> None:
    group = create_collection(
        session=db_session,
        collection_name="group",
        sample_type=SampleType.GROUP,
    )
    with pytest.raises(ValueError, match="Duplicate component name 'comp' in group components."):
        collection_resolver.create_group_components(
            session=db_session,
            parent_collection_id=group.collection_id,
            components=[("comp", SampleType.IMAGE), ("comp", SampleType.VIDEO)],
        )
