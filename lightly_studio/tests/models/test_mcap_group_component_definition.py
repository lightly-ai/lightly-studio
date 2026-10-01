"""Tests for the McapGroupComponentDefinition model."""

import pytest
from sqlalchemy.exc import DatabaseError
from sqlmodel import Session, text

from lightly_studio.models.collection import SampleType
from lightly_studio.models.mcap_group_component_definition import (
    McapDataType,
    McapGroupComponentDefinitionTable,
)
from lightly_studio.resolvers import collection_resolver
from tests.helpers_resolvers import create_collection


class TestMcapDataTypeColumn:
    """Tests for the ``mcap_data_type`` column."""

    def test_accepts_enum_members(self, db_session: Session) -> None:
        """Both MCAP data types round-trip through the database."""
        parent = create_collection(session=db_session, sample_type=SampleType.GROUP)
        components = collection_resolver.create_group_components(
            session=db_session,
            parent_collection_id=parent.collection_id,
            components=[("image", SampleType.MCAP), ("point_cloud", SampleType.MCAP)],
        )
        image_id = components["image"].collection_id
        point_cloud_id = components["point_cloud"].collection_id
        db_session.add(
            McapGroupComponentDefinitionTable(
                collection_id=image_id,
                mcap_data_type=McapDataType.VIDEO_FRAME,
                frame_id="main",
                channel_id=3,
            )
        )
        db_session.add(
            McapGroupComponentDefinitionTable(
                collection_id=point_cloud_id,
                mcap_data_type=McapDataType.POINT_CLOUD,
                channel_id=5,
            )
        )
        db_session.commit()
        db_session.expire_all()

        image = db_session.get(McapGroupComponentDefinitionTable, image_id)
        point_cloud = db_session.get(McapGroupComponentDefinitionTable, point_cloud_id)

        assert image is not None
        assert point_cloud is not None
        assert image.mcap_data_type == McapDataType.VIDEO_FRAME
        assert image.frame_id == "main"
        assert image.channel_id == 3
        assert point_cloud.mcap_data_type == McapDataType.POINT_CLOUD
        assert point_cloud.frame_id is None
        assert point_cloud.channel_id == 5

    def test_rejects_value_outside_enum(self, db_session: Session) -> None:
        """The database refuses a raw insert with an unknown MCAP data type.

        The ORM never produces such a value, so this guards raw SQL writers such as the
        deep copy INSERT ... SELECT.
        """
        parent = create_collection(session=db_session, sample_type=SampleType.GROUP)
        components = collection_resolver.create_group_components(
            session=db_session,
            parent_collection_id=parent.collection_id,
            components=[("image", SampleType.MCAP)],
        )
        collection_id = components["image"].collection_id

        with pytest.raises(DatabaseError):
            db_session.exec(  # type: ignore[call-overload]
                text(
                    "INSERT INTO mcap_group_component_definition "
                    "(collection_id, mcap_data_type, channel_id) "
                    "VALUES (:collection_id, 'BOGUS', 1)"
                ),
                params={"collection_id": str(collection_id)},
            )
        db_session.rollback()

        assert db_session.get(McapGroupComponentDefinitionTable, collection_id) is None
