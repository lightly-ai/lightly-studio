from sqlmodel import Session

from lightly_studio.core.mcap.mcap_sample import McapSample
from lightly_studio.models.collection import SampleType
from tests.helpers_resolvers import create_collection, create_mcap


class TestMcapSample:
    def test_mcap_sample(self, db_session: Session) -> None:
        collection = create_collection(session=db_session, sample_type=SampleType.MCAP)
        collection_id = collection.collection_id

        mcap_table = create_mcap(
            session=db_session,
            collection_id=collection_id,
            channel_id=3,
            log_time_ns=100,
            capture_timestamp_ns=100,
            keyframe_log_time_ns=90,
        )

        sample = McapSample(inner=mcap_table)
        assert sample.channel_id == 3
        assert sample.log_time_ns == 100
        assert sample.capture_timestamp_ns == 100
        assert sample.keyframe_log_time_ns == 90
        assert sample.collection_id == collection_id
        assert sample.sample_id == mcap_table.sample_id
