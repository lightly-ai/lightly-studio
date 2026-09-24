from sqlmodel import Session

from lightly_studio.core.mcap.create_mcap import CreateMcap
from lightly_studio.core.mcap.type_definitions import FrameLocator
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import mcap_resolver
from tests.helpers_resolvers import create_collection


class TestCreateMcap:
    def test_from_frame_locator(self) -> None:
        locator = FrameLocator(
            channel_id=3,
            log_time_ns=1_000_000_000,
            capture_timestamp_ns=950_000_000,
            topic="/cam/front/compressed_video",
            keyframe_log_time_ns=900_000_000,
            schema_name="foxglove_msgs/CompressedVideo",
        )

        creator = CreateMcap.from_frame_locator(locator=locator)

        assert creator == CreateMcap(
            channel_id=3,
            log_time_ns=1_000_000_000,
            capture_timestamp_ns=950_000_000,
            keyframe_log_time_ns=900_000_000,
        )

    def test_from_frame_locator__point_cloud(self) -> None:
        locator = FrameLocator(
            channel_id=5,
            log_time_ns=1_050_000_000,
            capture_timestamp_ns=1_040_000_000,
            topic="/lidar/points",
        )

        creator = CreateMcap.from_frame_locator(locator=locator)

        assert creator.keyframe_log_time_ns is None
        assert creator.capture_timestamp_ns == 1_040_000_000

    def test_create_in_collection(self, db_session: Session) -> None:
        collection = create_collection(session=db_session, sample_type=SampleType.MCAP)
        creator = CreateMcap(
            channel_id=3,
            log_time_ns=100,
            capture_timestamp_ns=100,
            keyframe_log_time_ns=90,
        )

        sample_id = creator.create_in_collection(
            session=db_session, collection_id=collection.collection_id
        )

        mcap = mcap_resolver.get_by_id(session=db_session, sample_id=sample_id)
        assert mcap is not None
        assert mcap.channel_id == 3
        assert mcap.log_time_ns == 100
        assert mcap.capture_timestamp_ns == 100
        assert mcap.keyframe_log_time_ns == 90
        assert mcap.sample.collection_id == collection.collection_id

    def test_sample_type(self) -> None:
        creator = CreateMcap(
            channel_id=5,
            log_time_ns=100,
            capture_timestamp_ns=100,
        )
        assert creator.sample_type() == SampleType.MCAP
