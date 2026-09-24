"""Tests for the mcap_sequence_ticks models."""

from uuid import uuid4

from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.models.mcap import McapTable
from lightly_studio.models.mcap_sequence_ticks import (
    TickChannelView,
    TickDetailView,
    TickListView,
    TickView,
)
from lightly_studio.models.sample import SampleTable
from tests.helpers_resolvers import create_collection


class TestTickView:
    def test_fields(self) -> None:
        """TickView holds seq_number and timestamp_ns."""
        tick = TickView(seq_number=0, timestamp_ns=1_000)
        assert tick.seq_number == 0
        assert tick.timestamp_ns == 1_000

    def test_timestamp_ns__none(self) -> None:
        """timestamp_ns accepts None."""
        tick = TickView(seq_number=2, timestamp_ns=None)
        assert tick.timestamp_ns is None


class TestTickListView:
    def test_ticks(self) -> None:
        """TickListView wraps a list of TickView."""
        ticks = [TickView(seq_number=0, timestamp_ns=100), TickView(seq_number=1, timestamp_ns=200)]
        view = TickListView(ticks=ticks)
        assert len(view.ticks) == 2
        assert view.ticks[0].seq_number == 0
        assert view.ticks[1].seq_number == 1

    def test_empty(self) -> None:
        """TickListView accepts an empty tick list."""
        view = TickListView(ticks=[])
        assert view.ticks == []


class TestTickChannelView:
    def test_from_mcap_table__camera(self, db_session: Session) -> None:
        """from_mcap_table copies all three locator fields for a camera channel."""
        collection = create_collection(session=db_session, sample_type=SampleType.MCAP)
        sample = SampleTable(collection_id=collection.collection_id)
        db_session.add(sample)
        db_session.commit()

        mcap = McapTable(
            sample_id=sample.sample_id,
            channel_id=3,
            log_time_ns=100,
            capture_timestamp_ns=95,
            keyframe_log_time_ns=80,
        )
        db_session.add(mcap)
        db_session.commit()
        db_session.refresh(mcap)

        view = TickChannelView.from_mcap_table(mcap=mcap, group_component_name="front")

        assert view.channel_id == 3
        assert view.group_component_name == "front"
        assert view.log_time_ns == "100"
        assert view.keyframe_log_time_ns == "80"

    def test_from_mcap_table__point_cloud(self, db_session: Session) -> None:
        """from_mcap_table leaves keyframe_log_time_ns as None for a lidar channel."""
        collection = create_collection(session=db_session, sample_type=SampleType.MCAP)
        sample = SampleTable(collection_id=collection.collection_id)
        db_session.add(sample)
        db_session.commit()

        mcap = McapTable(
            sample_id=sample.sample_id,
            channel_id=7,
            log_time_ns=200,
            capture_timestamp_ns=200,
        )
        db_session.add(mcap)
        db_session.commit()
        db_session.refresh(mcap)

        view = TickChannelView.from_mcap_table(mcap=mcap, group_component_name="pcl_front")

        assert view.channel_id == 7
        assert view.group_component_name == "pcl_front"
        assert view.log_time_ns == "200"
        assert view.keyframe_log_time_ns is None


class TestTickDetailView:
    def test_fields(self) -> None:
        """TickDetailView exposes recording_id, seq_number, timestamp_ns, and channels."""
        recording_id = uuid4()
        channel = TickChannelView(
            channel_id=1,
            group_component_name="front",
            log_time_ns="500",
            keyframe_log_time_ns=None,
        )
        detail = TickDetailView(
            recording_id=recording_id,
            seq_number=0,
            timestamp_ns=500,
            channels={"front": channel},
        )
        assert detail.recording_id == recording_id
        assert detail.seq_number == 0
        assert detail.timestamp_ns == 500
        assert detail.channels["front"].channel_id == 1

    def test_timestamp_ns__none(self) -> None:
        """TickDetailView accepts None for timestamp_ns."""
        detail = TickDetailView(
            recording_id=uuid4(),
            seq_number=1,
            timestamp_ns=None,
            channels={},
        )
        assert detail.timestamp_ns is None
