"""Tests for get_by_collection_id of MCAP group component definitions."""

from sqlmodel import Session

from lightly_studio.models.mcap_group_component_definition import McapDataType
from lightly_studio.resolvers import mcap_group_component_definition_resolver
from tests.resolvers.mcap_group_component_definition_resolver import helpers


def test_get_by_collection_id(db_session: Session) -> None:
    _, children = helpers.create_mcap_group_components(session=db_session)
    collection_id = children["image"].collection_id
    mcap_group_component_definition_resolver.create(
        session=db_session,
        collection_id=collection_id,
        mcap_data_type=McapDataType.VIDEO_FRAME,
        channel_id=3,
    )

    row = mcap_group_component_definition_resolver.get_by_collection_id(
        session=db_session, collection_id=collection_id
    )

    assert row is not None
    assert row.collection_id == collection_id
    assert row.mcap_data_type == McapDataType.VIDEO_FRAME
    assert row.channel_id == 3


def test_get_by_collection_id__classic_group(db_session: Session) -> None:
    _, children = helpers.create_classic_group_components(session=db_session)

    assert (
        mcap_group_component_definition_resolver.get_by_collection_id(
            session=db_session, collection_id=children["image"].collection_id
        )
        is None
    )
    assert (
        mcap_group_component_definition_resolver.get_by_collection_id(
            session=db_session, collection_id=children["video"].collection_id
        )
        is None
    )
