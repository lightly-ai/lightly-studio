from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import (
    video_resolver,
)
from tests.helpers_resolvers import create_collection
from tests.resolvers.video.helpers import VideoStub, create_videos


def test_get_view_by_id(db_session: Session) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    collection_id = collection.collection_id

    create_videos(
        session=db_session,
        collection_id=collection_id,
        videos=[
            VideoStub(path="/path/to/sample1.mp4"),
            VideoStub(path="/path/to/sample2.mp4"),
        ],
    )

    videos = video_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection_id,
    ).samples

    result = video_resolver.get_view_by_id(session=db_session, sample_id=videos[0].sample_id)

    assert result is not None
    assert result.file_name == "sample1.mp4"
