"""Tests for get_named_data_types_by_group_collection_id of MCAP definitions."""

from sqlmodel import Session

from lightly_studio.models.mcap_group_component_definition import McapDataType
from lightly_studio.resolvers import mcap_group_component_definition_resolver
from tests.resolvers.mcap_group_component_definition_resolver import helpers


def test_get_named_data_types_by_group_collection_id(db_session: Session) -> None:
    group, children = helpers.create_mcap_group_components(session=db_session)
    # Created in the reverse of the slot order, so the order is not the creation one.
    mcap_group_component_definition_resolver.create(
        session=db_session,
        collection_id=children["point_cloud"].collection_id,
        mcap_data_type=McapDataType.POINT_CLOUD,
    )
    mcap_group_component_definition_resolver.create(
        session=db_session,
        collection_id=children["image"].collection_id,
        mcap_data_type=McapDataType.VIDEO_FRAME,
    )

    assert mcap_group_component_definition_resolver.get_named_data_types_by_group_collection_id(
        session=db_session, group_collection_id=group.collection_id
    ) == [
        ("image", McapDataType.VIDEO_FRAME),
        ("point_cloud", McapDataType.POINT_CLOUD),
    ]


def test_get_named_data_types_by_group_collection_id__without_mcap_definitions(
    db_session: Session,
) -> None:
    group, _ = helpers.create_classic_group_components(session=db_session)

    # A classic IMAGE/VIDEO slot has no MCAP definition, so it is left out.
    assert (
        mcap_group_component_definition_resolver.get_named_data_types_by_group_collection_id(
            session=db_session, group_collection_id=group.collection_id
        )
        == []
    )
