"""Tests for the get_point_cloud_mcaps_by_group_sample_ids resolver."""

from __future__ import annotations

from uuid import uuid4

from sqlmodel import Session

from lightly_studio.resolvers import group_resolver, mcap_resolver
from tests.helpers_resolvers import create_mcap
from tests.resolvers.mcap_group_sequence_resolver.helpers import create_mcap_sequence


def test_get_point_cloud_mcaps_by_group_sample_ids(db_session: Session) -> None:
    fixture = create_mcap_sequence(session=db_session)
    camera = create_mcap(
        session=db_session, collection_id=fixture.slots["front"].collection_id, channel_id=3
    )
    first_lidar = create_mcap(
        session=db_session,
        collection_id=fixture.slots["pcl_front"].collection_id,
        channel_id=7,
        log_time_ns=1_001,
    )
    second_lidar = create_mcap(
        session=db_session,
        collection_id=fixture.slots["pcl_front"].collection_id,
        channel_id=7,
        log_time_ns=2_001,
    )
    group_ids = group_resolver.create_many(
        session=db_session,
        collection_id=fixture.group_collection.collection_id,
        groups=[{camera.sample_id, first_lidar.sample_id}, {second_lidar.sample_id}],
    )

    result = mcap_resolver.get_point_cloud_mcaps_by_group_sample_ids(
        session=db_session, group_sample_ids=group_ids
    )

    assert {group_id: [m.log_time_ns for m in mcaps] for group_id, mcaps in result.items()} == {
        group_ids[0]: [1_001],
        group_ids[1]: [2_001],
    }


def test_get_point_cloud_mcaps_by_group_sample_ids__without_point_cloud(
    db_session: Session,
) -> None:
    fixture = create_mcap_sequence(session=db_session)
    camera = create_mcap(
        session=db_session, collection_id=fixture.slots["front"].collection_id, channel_id=3
    )
    group_ids = group_resolver.create_many(
        session=db_session,
        collection_id=fixture.group_collection.collection_id,
        groups=[{camera.sample_id}],
    )

    result = mcap_resolver.get_point_cloud_mcaps_by_group_sample_ids(
        session=db_session, group_sample_ids=group_ids
    )

    assert result == {}


def test_get_point_cloud_mcaps_by_group_sample_ids__empty(db_session: Session) -> None:
    result = mcap_resolver.get_point_cloud_mcaps_by_group_sample_ids(
        session=db_session, group_sample_ids=[]
    )

    assert result == {}


def test_get_point_cloud_mcaps_by_group_sample_ids__unknown_group(db_session: Session) -> None:
    result = mcap_resolver.get_point_cloud_mcaps_by_group_sample_ids(
        session=db_session, group_sample_ids=[uuid4()]
    )

    assert result == {}
