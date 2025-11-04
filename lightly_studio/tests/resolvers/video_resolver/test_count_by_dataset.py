from sqlmodel import Session

from lightly_studio.resolvers import (
    video_resolver,
)
from tests.helpers_resolvers import (
    create_dataset,
)
from tests.resolvers.video_resolver.helpers import VideoStub, create_videos


def test_count_by_dataset_id(test_db: Session) -> None:
    """Test counting samples by dataset ID."""
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.dataset_id

    # Initially should be 0
    assert video_resolver.count_by_dataset_id(session=test_db, dataset_id=dataset_id) == 0

    # Create some samples
    create_videos(
        session=test_db,
        dataset_id=dataset_id,
        videos=[
            VideoStub(path="/path/to/video_0.mp4"),
            VideoStub(path="/path/to/video_1.mp4"),
        ],
    )

    # Should now count 3 samples
    assert video_resolver.count_by_dataset_id(session=test_db, dataset_id=dataset_id) == 2

    # Create another dataset to ensure count is dataset-specific
    dataset2 = create_dataset(session=test_db, dataset_name="dataset2")
    dataset2_id = dataset2.dataset_id

    create_videos(
        session=test_db,
        dataset_id=dataset2_id,
        videos=[VideoStub(path="/path/to/video_other.mp4")],
    )
    # Counts should be independent
    assert video_resolver.count_by_dataset_id(session=test_db, dataset_id=dataset_id) == 2
    assert video_resolver.count_by_dataset_id(session=test_db, dataset_id=dataset2_id) == 1
