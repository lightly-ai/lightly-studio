import pytest
from sqlmodel import Session

from lightly_studio.core.group_sample import GroupSample
from lightly_studio.core.image_sample import ImageSample
from lightly_studio.core.video_sample import VideoSample
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import collection_resolver, group_resolver
from tests.helpers_resolvers import create_collection, create_image
from tests.resolvers.video.helpers import VideoStub, create_video


class TestGroupSample:
    def test_group_sample(self, db_session: Session) -> None:
        # Create collections
        group_col = create_collection(session=db_session, sample_type=SampleType.GROUP)
        components = collection_resolver.create_group_components(
            session=db_session,
            parent_collection_id=group_col.collection_id,
            components=[
                ("img", SampleType.IMAGE),
                ("vid", SampleType.VIDEO),
                ("extra", SampleType.IMAGE),
            ],
        )

        # Create component samples
        image_table = create_image(
            session=db_session,
            collection_id=components["img"].collection_id,
            file_path_abs="front_0.jpg",
        )
        video_table = create_video(
            session=db_session,
            collection_id=components["vid"].collection_id,
            video=VideoStub(path="back_0.mp4"),
        )

        # Create a group
        group_id = group_resolver.create_many(
            session=db_session,
            collection_id=group_col.collection_id,
            groups=[{image_table.sample_id, video_table.sample_id}],
        )[0]
        group_table = group_resolver.get_by_id(session=db_session, sample_id=group_id)
        assert group_table is not None

        # Instantiate GroupSample
        group = GroupSample(inner=group_table)

        # Access properties
        assert group.sample_id == group_id
