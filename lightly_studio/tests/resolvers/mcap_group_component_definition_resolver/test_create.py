"""Tests for creating MCAP group component definitions."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.models.mcap_group_component_definition import McapDataType
from lightly_studio.resolvers import mcap_group_component_definition_resolver
from tests.helpers_resolvers import create_collection
from tests.resolvers.mcap_group_component_definition_resolver import helpers


def test_create(db_session: Session) -> None:
    _, children = helpers.create_mcap_group_components(session=db_session)

    image_id = mcap_group_component_definition_resolver.create(
        session=db_session,
        collection_id=children["image"].collection_id,
        mcap_data_type=McapDataType.VIDEO_FRAME,
        channel_id=3,
        frame_id="main",
    )
    point_cloud_id = mcap_group_component_definition_resolver.create(
        session=db_session,
        collection_id=children["point_cloud"].collection_id,
        mcap_data_type=McapDataType.POINT_CLOUD,
        channel_id=5,
        frame_id="livox_front_left",
    )

    image = mcap_group_component_definition_resolver.get_by_collection_id(
        session=db_session, collection_id=image_id
    )
    point_cloud = mcap_group_component_definition_resolver.get_by_collection_id(
        session=db_session, collection_id=point_cloud_id
    )

    assert image is not None
    assert children["image"].group_component_definition is not None
    assert image.collection_id == children["image"].collection_id
    assert image.collection_id == children["image"].group_component_definition.collection_id
    assert image.mcap_data_type == McapDataType.VIDEO_FRAME
    assert image.channel_id == 3
    assert image.frame_id == "main"

    assert point_cloud is not None
    assert point_cloud.collection_id == children["point_cloud"].collection_id
    assert point_cloud.mcap_data_type == McapDataType.POINT_CLOUD
    assert point_cloud.channel_id == 5
    assert point_cloud.frame_id == "livox_front_left"


@pytest.mark.parametrize("frame_id", [None, "", "   "])
def test_create__optional_frame_id(db_session: Session, frame_id: str | None) -> None:
    _, children = helpers.create_mcap_group_components(session=db_session)

    collection_id = mcap_group_component_definition_resolver.create(
        session=db_session,
        collection_id=children["image"].collection_id,
        mcap_data_type=McapDataType.VIDEO_FRAME,
        channel_id=3,
        frame_id=frame_id,
    )

    definition = mcap_group_component_definition_resolver.get_by_collection_id(
        session=db_session, collection_id=collection_id
    )

    assert definition is not None
    assert definition.frame_id is None


def test_create__rejects_non_mcap_collection(db_session: Session) -> None:
    _, children = helpers.create_classic_group_components(session=db_session)

    with pytest.raises(ValueError, match="is having sample type 'image', expected 'mcap'"):
        mcap_group_component_definition_resolver.create(
            session=db_session,
            collection_id=children["image"].collection_id,
            mcap_data_type=McapDataType.VIDEO_FRAME,
            channel_id=3,
        )


def test_create__rejects_missing_gcd(db_session: Session) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.MCAP)

    with pytest.raises(ValueError, match="does not exist"):
        mcap_group_component_definition_resolver.create(
            session=db_session,
            collection_id=collection.collection_id,
            mcap_data_type=McapDataType.VIDEO_FRAME,
            channel_id=3,
        )


def test_create__rejects_unknown_collection_id(db_session: Session) -> None:
    with pytest.raises(ValueError, match="does not exist"):
        mcap_group_component_definition_resolver.create(
            session=db_session,
            collection_id=uuid4(),
            mcap_data_type=McapDataType.VIDEO_FRAME,
            channel_id=3,
        )


def test_create__duplicate_collection_id(db_session: Session) -> None:
    _, children = helpers.create_mcap_group_components(session=db_session)
    collection_id = children["image"].collection_id
    mcap_group_component_definition_resolver.create(
        session=db_session,
        collection_id=collection_id,
        mcap_data_type=McapDataType.VIDEO_FRAME,
        channel_id=3,
    )

    with pytest.raises(IntegrityError):
        mcap_group_component_definition_resolver.create(
            session=db_session,
            collection_id=collection_id,
            mcap_data_type=McapDataType.POINT_CLOUD,
            channel_id=5,
        )
    db_session.rollback()
