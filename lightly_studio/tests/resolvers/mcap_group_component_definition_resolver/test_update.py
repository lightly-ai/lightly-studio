"""Tests for updating MCAP group component definitions."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlmodel import Session

from lightly_studio.models.mcap_group_component_definition import McapDataType
from lightly_studio.resolvers import mcap_group_component_definition_resolver
from tests.resolvers.mcap_group_component_definition_resolver import helpers


def test_update(db_session: Session) -> None:
    _, children = helpers.create_mcap_group_components(session=db_session)
    collection_id = mcap_group_component_definition_resolver.create(
        session=db_session,
        collection_id=children["image"].collection_id,
        mcap_data_type=McapDataType.VIDEO_FRAME,
    )

    definition = mcap_group_component_definition_resolver.update(
        session=db_session, collection_id=collection_id, channel_id=3, frame_id="main"
    )

    assert definition.channel_id == 3
    assert definition.frame_id == "main"
    assert definition.mcap_data_type == McapDataType.VIDEO_FRAME


def test_update__first_write_wins(db_session: Session) -> None:
    _, children = helpers.create_mcap_group_components(session=db_session)
    collection_id = mcap_group_component_definition_resolver.create(
        session=db_session,
        collection_id=children["image"].collection_id,
        mcap_data_type=McapDataType.VIDEO_FRAME,
    )
    mcap_group_component_definition_resolver.update(
        session=db_session, collection_id=collection_id, channel_id=3, frame_id="main"
    )

    definition = mcap_group_component_definition_resolver.update(
        session=db_session, collection_id=collection_id, channel_id=9, frame_id="other"
    )

    assert definition.channel_id == 3
    assert definition.frame_id == "main"


def test_update__partial(db_session: Session) -> None:
    _, children = helpers.create_mcap_group_components(session=db_session)
    collection_id = mcap_group_component_definition_resolver.create(
        session=db_session,
        collection_id=children["image"].collection_id,
        mcap_data_type=McapDataType.VIDEO_FRAME,
    )

    mcap_group_component_definition_resolver.update(
        session=db_session, collection_id=collection_id, channel_id=3
    )
    definition = mcap_group_component_definition_resolver.update(
        session=db_session, collection_id=collection_id, frame_id="main"
    )

    assert definition.channel_id == 3
    assert definition.frame_id == "main"


def test_update__blank_frame_id(db_session: Session) -> None:
    _, children = helpers.create_mcap_group_components(session=db_session)
    collection_id = mcap_group_component_definition_resolver.create(
        session=db_session,
        collection_id=children["image"].collection_id,
        mcap_data_type=McapDataType.VIDEO_FRAME,
    )

    definition = mcap_group_component_definition_resolver.update(
        session=db_session, collection_id=collection_id, frame_id="   "
    )

    assert definition.frame_id is None


def test_update__missing_definition(db_session: Session) -> None:
    with pytest.raises(ValueError, match="does not exist"):
        mcap_group_component_definition_resolver.update(
            session=db_session, collection_id=uuid4(), channel_id=3
        )
