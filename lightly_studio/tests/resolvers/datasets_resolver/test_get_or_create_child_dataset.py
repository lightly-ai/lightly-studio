from __future__ import annotations

import uuid

import pytest
from sqlmodel import Session

from lightly_studio.models.collection import CollectionCreate, SampleType
from lightly_studio.resolvers import collection_resolver


def test_get_or_create_child_dataset(
    db_session: Session,
) -> None:
    """Test creating a video frame child dataset."""
    # First tree
    video_dataset = collection_resolver.create(
        session=db_session, dataset=CollectionCreate(name="videos", sample_type=SampleType.VIDEO)
    )
    # A new video frame child dataset should be created.
    video_frames_dataset_id = collection_resolver.get_or_create_child_dataset(
        session=db_session,
        dataset_id=video_dataset.collection_id,
        sample_type=SampleType.VIDEO_FRAME,
    )

    video_frames_dataset = collection_resolver.get_by_id(
        session=db_session, dataset_id=video_frames_dataset_id
    )
    assert video_frames_dataset is not None
    assert video_frames_dataset.sample_type == SampleType.VIDEO_FRAME
    assert video_frames_dataset.parent_collection_id == video_dataset.collection_id
    assert video_frames_dataset.name == "videos__video_frame"

    # Calling again should return the same dataset ID.
    same_video_frames_dataset_id = collection_resolver.get_or_create_child_dataset(
        session=db_session,
        dataset_id=video_dataset.collection_id,
        sample_type=SampleType.VIDEO_FRAME,
    )
    assert same_video_frames_dataset_id == video_frames_dataset_id

    # No new dataset should be created.
    datasets = collection_resolver.get_hierarchy(
        session=db_session, root_dataset_id=video_dataset.collection_id
    )
    assert len(datasets) == 2
    assert datasets[1].collection_id == video_frames_dataset_id


def test_get_or_create_child_dataset__existing_non_video_frame_dataset_child(
    db_session: Session,
) -> None:
    """Test creating a video frame child dataset."""
    # Create a video dataset with a image child dataset.
    video_dataset = collection_resolver.create(
        session=db_session, dataset=CollectionCreate(name="videos", sample_type=SampleType.VIDEO)
    )
    image_dataset = collection_resolver.create(
        session=db_session,
        dataset=CollectionCreate(
            name="images",
            sample_type=SampleType.IMAGE,
            parent_collection_id=video_dataset.collection_id,
        ),
    )
    # A new video frame child dataset should be created, because the child dataset is of type Image.
    video_frames_dataset_id = collection_resolver.get_or_create_child_dataset(
        session=db_session,
        dataset_id=video_dataset.collection_id,
        sample_type=SampleType.VIDEO_FRAME,
    )
    # Ensure that the new video frame child dataset is different from the existing image
    # child dataset.
    assert video_frames_dataset_id != image_dataset.collection_id

    # New child should be created even though there is already a child dataset
    # with a different sample type.
    datasets = collection_resolver.get_hierarchy(
        session=db_session, root_dataset_id=video_dataset.collection_id
    )
    assert len(datasets) == 3
    assert datasets[1].collection_id == image_dataset.collection_id
    assert datasets[2].collection_id == video_frames_dataset_id


def test_get_or_create_child_dataset__non_existent(
    db_session: Session,
) -> None:
    non_existent_id = uuid.uuid4()
    with pytest.raises(ValueError, match=f"Dataset with id {non_existent_id} not found"):
        collection_resolver.get_or_create_child_dataset(
            session=db_session,
            dataset_id=non_existent_id,
            sample_type=SampleType.CAPTION,
        )


def test_get_or_create_child_dataset__multiple_existing_video_frame_datasets(
    db_session: Session,
) -> None:
    # Test that an error is raised if the there are multiple video frame datasets.
    video_dataset_id = collection_resolver.create(
        session=db_session, dataset=CollectionCreate(name="videos", sample_type=SampleType.VIDEO)
    ).collection_id
    collection_resolver.create(
        session=db_session,
        dataset=CollectionCreate(
            name="videos_video_frames_1",
            sample_type=SampleType.VIDEO_FRAME,
            parent_collection_id=video_dataset_id,
        ),
    )
    collection_resolver.create(
        session=db_session,
        dataset=CollectionCreate(
            name="videos_video_frames_2",
            sample_type=SampleType.VIDEO_FRAME,
            parent_collection_id=video_dataset_id,
        ),
    )

    with pytest.raises(
        ValueError,
        match="Multiple child datasets with sample type video_frame found for dataset",
    ):
        collection_resolver.get_or_create_child_dataset(
            session=db_session, dataset_id=video_dataset_id, sample_type=SampleType.VIDEO_FRAME
        )


def test_get_or_create_child_dataset__return_direct_child(
    db_session: Session,
) -> None:
    dataset_id = collection_resolver.create(
        session=db_session, dataset=CollectionCreate(name="images", sample_type=SampleType.IMAGE)
    ).collection_id

    # Create a direct captions child dataset
    child_dataset_id = collection_resolver.get_or_create_child_dataset(
        session=db_session, dataset_id=dataset_id, sample_type=SampleType.CAPTION
    )

    # Create a nested captions child dataset
    grandchild_dataset_id = collection_resolver.get_or_create_child_dataset(
        session=db_session, dataset_id=child_dataset_id, sample_type=SampleType.CAPTION
    )
    assert child_dataset_id != grandchild_dataset_id

    # Fetching the captions child dataset of the root dataset should return the direct child
    fetched_child_dataset_id = collection_resolver.get_or_create_child_dataset(
        session=db_session, dataset_id=dataset_id, sample_type=SampleType.CAPTION
    )
    assert fetched_child_dataset_id == child_dataset_id
