"""Tests for datasets_resolver - get_or_create_video_frame_child functionality."""

from __future__ import annotations

import pytest
from sqlmodel import Session

from lightly_studio.models.dataset import DatasetCreate, SampleType
from lightly_studio.resolvers import dataset_resolver


def test_get_or_create_video_frame_child(
    db_session: Session,
) -> None:
    """Test creating a video frame child dataset."""
    # First tree
    video_dataset = dataset_resolver.create(
        session=db_session, dataset=DatasetCreate(name="videos", sample_type=SampleType.VIDEO)
    )
    # A new video frame child dataset should be created.
    video_frames_dataset_id = dataset_resolver.get_or_create_video_frame_child(
        session=db_session, dataset_id=video_dataset.dataset_id
    )

    video_frames_dataset = dataset_resolver.get_by_id(
        session=db_session, dataset_id=video_frames_dataset_id
    )
    assert video_frames_dataset is not None
    assert video_frames_dataset.sample_type == SampleType.VIDEO_FRAME
    assert video_frames_dataset.parent_dataset_id == video_dataset.dataset_id
    assert video_frames_dataset.name == "videos__video_frames"

    # Calling again should return the same dataset ID.
    same_video_frames_dataset_id = dataset_resolver.get_or_create_video_frame_child(
        session=db_session, dataset_id=video_dataset.dataset_id
    )
    assert same_video_frames_dataset_id == video_frames_dataset_id

    # No new dataset should be created.
    datasets = dataset_resolver.get_hierarchy(
        session=db_session, root_dataset_id=video_dataset.dataset_id
    )
    assert len(datasets) == 2
    assert datasets[1].dataset_id == video_frames_dataset_id


def test_get_or_create_video_frame_child__existing_non_video_frame_dataset_child(
    db_session: Session,
) -> None:
    """Test creating a video frame child dataset."""
    # Create a video dataset with a image child dataset.
    video_dataset = dataset_resolver.create(
        session=db_session, dataset=DatasetCreate(name="videos", sample_type=SampleType.VIDEO)
    )
    image_dataset = dataset_resolver.create(
        session=db_session,
        dataset=DatasetCreate(
            name="images", sample_type=SampleType.IMAGE, parent_dataset_id=video_dataset.dataset_id
        ),
    )
    # A new video frame child dataset should be created, because the child dataset is of type Image.
    video_frames_dataset_id = dataset_resolver.get_or_create_video_frame_child(
        session=db_session, dataset_id=video_dataset.dataset_id
    )
    # Ensure that the new video frame child dataset is different from the existing image child dataset.
    assert video_frames_dataset_id != image_dataset.dataset_id

    # New child should be created even though there is already a child dataset
    # with a different sample type.
    datasets = dataset_resolver.get_hierarchy(
        session=db_session, root_dataset_id=video_dataset.dataset_id
    )
    assert len(datasets) == 3
    assert datasets[1].dataset_id == video_frames_dataset_id
    assert datasets[2].dataset_id == image_dataset.dataset_id


def test_get_or_create_video_frame_child__wrong_dataset_sample_type(
    db_session: Session,
) -> None:
    # Test that an error is raised if the dataset is not of type VIDEO.
    image_dataset = dataset_resolver.create(
        session=db_session, dataset=DatasetCreate(name="images", sample_type=SampleType.IMAGE)
    )
    with pytest.raises(ValueError, match="is having sample type 'image', expected 'video'"):
        dataset_resolver.get_or_create_video_frame_child(
            session=db_session, dataset_id=image_dataset.dataset_id
        )


def test_get_or_create_video_frame_child__multiple_existing_video_frame_datasets(
    db_session: Session,
) -> None:
    # Test that an error is raised if the there are multiple video frame datasets.
    video_dataset_id = dataset_resolver.create(
        session=db_session, dataset=DatasetCreate(name="videos", sample_type=SampleType.VIDEO)
    ).dataset_id
    dataset_resolver.create(
        session=db_session,
        dataset=DatasetCreate(
            name="videos_video_frames_1",
            sample_type=SampleType.VIDEO_FRAME,
            parent_dataset_id=video_dataset_id,
        ),
    )
    dataset_resolver.create(
        session=db_session,
        dataset=DatasetCreate(
            name="videos_video_frames_2",
            sample_type=SampleType.VIDEO_FRAME,
            parent_dataset_id=video_dataset_id,
        ),
    )

    with pytest.raises(
        ValueError,
        match=f"Multiple video frame child datasets found for dataset id {video_dataset_id}",
    ):
        dataset_resolver.get_or_create_video_frame_child(
            session=db_session, dataset_id=video_dataset_id
        )
