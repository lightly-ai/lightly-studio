from __future__ import annotations

import pytest
from sqlmodel import Session

from lightly_studio.core.mcap.component import McapComponent
from lightly_studio.models.collection import SampleType
from lightly_studio.models.mcap_group_component_definition import McapDataType
from lightly_studio.resolvers import (
    collection_resolver,
    mcap_group_component_definition_resolver,
)
from tests.helpers_resolvers import create_collection


class TestMcapComponent:
    def test_properties(self, db_session: Session) -> None:
        component = _create_component(
            session=db_session, name="front", mcap_data_type=McapDataType.VIDEO_FRAME
        )

        assert component.name == "front"
        assert component.mcap_data_type == McapDataType.VIDEO_FRAME
        # The channel and the frame are filled by the first recording that is indexed.
        assert component.channel_id is None
        assert component.frame_id is None

    def test_properties__without_definition(self, db_session: Session) -> None:
        collection = create_collection(session=db_session, sample_type=SampleType.MCAP)
        component = McapComponent(
            session=db_session, collection_id=collection.collection_id, name="front"
        )

        with pytest.raises(RuntimeError, match="has no MCAP component definition"):
            component.mcap_data_type  # noqa: B018

    def test_update_mcap_definition(self, db_session: Session) -> None:
        component = _create_component(
            session=db_session, name="front", mcap_data_type=McapDataType.VIDEO_FRAME
        )

        component.update_mcap_definition(channel_id=7, frame_id="cam_front")

        assert component.channel_id == 7
        assert component.frame_id == "cam_front"

    def test_update_mcap_definition__first_write_wins(self, db_session: Session) -> None:
        component = _create_component(
            session=db_session, name="front", mcap_data_type=McapDataType.VIDEO_FRAME
        )
        component.update_mcap_definition(channel_id=7, frame_id="cam_front")

        # A second recording does not move the component to another channel.
        component.update_mcap_definition(channel_id=9, frame_id="cam_rear")

        assert component.channel_id == 7
        assert component.frame_id == "cam_front"

    def test_update_mcap_definition__partial(self, db_session: Session) -> None:
        component = _create_component(
            session=db_session, name="pcl_front", mcap_data_type=McapDataType.POINT_CLOUD
        )

        component.update_mcap_definition(channel_id=3)

        assert component.channel_id == 3
        assert component.frame_id is None


def _create_component(session: Session, name: str, mcap_data_type: McapDataType) -> McapComponent:
    """Create one MCAP component collection with its definition, and wrap it."""
    group_collection = create_collection(session=session, sample_type=SampleType.GROUP)
    component_collections = collection_resolver.create_group_components(
        session=session,
        parent_collection_id=group_collection.collection_id,
        components=[(name, SampleType.MCAP)],
    )
    collection_id = component_collections[name].collection_id
    mcap_group_component_definition_resolver.create(
        session=session, collection_id=collection_id, mcap_data_type=mcap_data_type
    )
    return McapComponent(session=session, collection_id=collection_id, name=name)
