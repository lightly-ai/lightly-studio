from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import video_frame_resolver
from tests.helpers_resolvers import (
    create_collection,
)
from tests.resolvers.video.helpers import VideoStub, create_video_with_frames


def test_get_table_fields_bounds(test_db: Session) -> None:
    dataset = create_collection(session=test_db, sample_type=SampleType.VIDEO)
    dataset_id = dataset.collection_id

    video_frames_data = create_video_with_frames(
        session=test_db,
        collection_id=dataset_id,
        video=VideoStub(path="/path/to/sample1.mp4", fps=5, duration_s=1),
    )

    bounds = video_frame_resolver.get_table_fields_bounds(
        session=test_db, collection_id=video_frames_data.video_frames_collection_id
    )

    assert bounds is not None
    assert bounds.frame_number.min == 0
    assert bounds.frame_number.max == 4
