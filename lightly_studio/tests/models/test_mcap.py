"""Tests for the Mcap model."""

from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.models.mcap import McapTable, McapView
from lightly_studio.models.sample import SampleTable
from tests.helpers_resolvers import create_collection


class TestMcapView:
    """Tests for the McapView model."""

    def test_from_mcap_table__camera(self, db_session: Session) -> None:
        """Conversion includes the keyframe log time for a camera channel."""
        collection = create_collection(session=db_session, sample_type=SampleType.MCAP)
        sample = SampleTable(collection_id=collection.collection_id)
        db_session.add(sample)
        db_session.commit()

        mcap = McapTable(
            sample_id=sample.sample_id,
            channel_id=3,
            log_time_ns=100,
            capture_timestamp_ns=95,
            keyframe_log_time_ns=90,
        )
        db_session.add(mcap)
        db_session.commit()
        db_session.refresh(mcap)

        mcap_view = McapView.from_mcap_table(mcap=mcap)

        assert mcap_view.sample_id == sample.sample_id
        assert mcap_view.channel_id == 3
        assert mcap_view.log_time_ns == 100
        assert mcap_view.capture_timestamp_ns == 95
        assert mcap_view.keyframe_log_time_ns == 90
        assert mcap_view.sample.sample_id == sample.sample_id

    def test_from_mcap_table__point_cloud(self, db_session: Session) -> None:
        """Conversion leaves the keyframe log time unset for a lidar channel."""
        collection = create_collection(session=db_session, sample_type=SampleType.MCAP)
        sample = SampleTable(collection_id=collection.collection_id)
        db_session.add(sample)
        db_session.commit()

        mcap = McapTable(
            sample_id=sample.sample_id,
            channel_id=5,
            log_time_ns=100,
            capture_timestamp_ns=100,
        )
        db_session.add(mcap)
        db_session.commit()
        db_session.refresh(mcap)

        mcap_view = McapView.from_mcap_table(mcap=mcap)

        assert mcap_view.channel_id == 5
        assert mcap_view.keyframe_log_time_ns is None
