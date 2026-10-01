"""Tests for get_all_by_group_collection_id of MCAP group component definitions."""

from sqlmodel import Session

from lightly_studio.models.mcap_group_component_definition import McapDataType
from lightly_studio.resolvers import mcap_group_component_definition_resolver
from tests.resolvers.mcap_group_component_definition_resolver import helpers


def test_get_all_by_group_collection_id(db_session: Session) -> None:
    group, children = helpers.create_mcap_group_components(session=db_session)
    mcap_group_component_definition_resolver.create(
        session=db_session,
        collection_id=children["image"].collection_id,
        mcap_data_type=McapDataType.VIDEO_FRAME,
        channel_id=3,
    )
    mcap_group_component_definition_resolver.create(
        session=db_session,
        collection_id=children["point_cloud"].collection_id,
        mcap_data_type=McapDataType.POINT_CLOUD,
        channel_id=5,
    )

    rows = mcap_group_component_definition_resolver.get_all_by_group_collection_id(
        session=db_session, group_collection_id=group.collection_id
    )

    assert len(rows) == 2
    by_collection_id = {row.collection_id: row for row in rows}
    assert by_collection_id[children["image"].collection_id].mcap_data_type == (
        McapDataType.VIDEO_FRAME
    )
    assert by_collection_id[children["image"].collection_id].channel_id == 3
    assert by_collection_id[children["point_cloud"].collection_id].mcap_data_type == (
        McapDataType.POINT_CLOUD
    )

    point_clouds = [row for row in rows if row.mcap_data_type == McapDataType.POINT_CLOUD]
    assert len(point_clouds) == 1
    assert point_clouds[0].collection_id == children["point_cloud"].collection_id
    assert point_clouds[0].channel_id == 5
