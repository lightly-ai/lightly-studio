from __future__ import annotations

from sqlmodel import Session

from lightly_studio.core.dataset_query.dataset_query import DatasetQuery
from lightly_studio.export import coco_captions
from tests.helpers_resolvers import (
    ImageStub,
    create_caption,
    create_dataset,
    create_images,
)


def test_to_coco_caption_dict(
    db_session: Session,
) -> None:
    """Tests conversion to COCO captions format."""
    dataset = create_dataset(session=db_session)
    images = create_images(
        db_session=db_session,
        dataset_id=dataset.dataset_id,
        images=[
            ImageStub(path="/path/image0.jpg", width=100, height=100),
            ImageStub(path="/path/image1.jpg", width=200, height=200),
        ],
    )

    # No captions for image0.jpg, two captions for image1.jpg
    create_caption(
        session=db_session,
        dataset_id=dataset.dataset_id,
        parent_sample_id=images[1].sample_id,
        text="caption one",
    )
    create_caption(
        session=db_session,
        dataset_id=dataset.dataset_id,
        parent_sample_id=images[1].sample_id,
        text="caption two",
    )

    # Call the function under test
    samples = DatasetQuery(dataset=dataset, session=db_session)
    coco_dict = coco_captions.to_coco_captions_dict(samples=samples)

    assert coco_dict == {
        "images": [
            {"id": 0, "file_name": "/path/image0.jpg", "width": 100, "height": 100},
            {"id": 1, "file_name": "/path/image1.jpg", "width": 200, "height": 200},
        ],
        "annotations": [
            {"id": 0, "image_id": 1, "caption": "caption one"},
            {"id": 1, "image_id": 1, "caption": "caption two"},
        ],
    }


def test_to_coco_caption_dict__empty(
    db_session: Session,
) -> None:
    """Tests conversion to COCO captions format."""
    dataset = create_dataset(session=db_session)

    # Call the function under test
    samples = DatasetQuery(dataset=dataset, session=db_session)
    coco_dict = coco_captions.to_coco_captions_dict(samples=samples)

    assert coco_dict == {"images": [], "annotations": []}
