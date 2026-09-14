"""Tests that classic IMAGE/VIDEO groups stay valid without an MCAP row."""

from sqlmodel import Session

from lightly_studio.models.group_component_definition import GroupComponentDefinitionTable
from lightly_studio.resolvers import collection_resolver, mcap_group_component_definition_resolver
from tests.resolvers.mcap_group_component_definition_resolver import helpers


def test_classic_group_components_unchanged(db_session: Session) -> None:
    group, created = helpers.create_classic_group_components(session=db_session)

    components = collection_resolver.get_group_components(
        session=db_session, parent_collection_id=group.collection_id
    )

    assert len(components) == 2
    assert components["image"].group_component_definition is not None
    assert components["image"].group_component_definition.group_component_name == "image"
    assert components["image"].group_component_definition.group_component_index == 0
    assert components["video"].group_component_definition is not None
    assert components["video"].group_component_definition.group_component_name == "video"
    assert components["video"].group_component_definition.group_component_index == 1

    image_gcd = db_session.get(GroupComponentDefinitionTable, created["image"].collection_id)
    video_gcd = db_session.get(GroupComponentDefinitionTable, created["video"].collection_id)
    assert image_gcd is not None
    assert video_gcd is not None
    assert (
        mcap_group_component_definition_resolver.get_by_collection_id(
            session=db_session, collection_id=created["image"].collection_id
        )
        is None
    )
    assert (
        mcap_group_component_definition_resolver.get_all_by_group_collection_id(
            session=db_session, group_collection_id=group.collection_id
        )
        == []
    )
