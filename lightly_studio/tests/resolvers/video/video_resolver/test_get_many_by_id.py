from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import (
    video_resolver,
)
from tests.helpers_resolvers import (
    create_collection,
)
from tests.resolvers.video.helpers import VideoStub, create_video


def test_get_many_by_id(
    test_db: Session,
) -> None:
    collection = create_collection(session=test_db, sample_type=SampleType.VIDEO)
    collection_id = collection.collection_id
    # Create samples.
    video1 = create_video(
        session=test_db,
        collection_id=collection_id,
        video=VideoStub(path="/path/to/sample1.mp4"),
    )
    video2 = create_video(
        session=test_db,
        collection_id=collection_id,
        video=VideoStub(path="/path/to/sample2.mp4"),
    )

    # Act.
    samples = video_resolver.get_many_by_id(
        session=test_db, sample_ids=[video1.sample_id, video2.sample_id]
    )

    # Assert.
    assert len(samples) == 2
    assert samples[0].file_name == "sample1.mp4"
    assert samples[1].file_name == "sample2.mp4"
