from __future__ import annotations

import json
from pathlib import Path

from labelformat.formats.labelformat import LabelformatObjectDetectionInput
from labelformat.model.bounding_box import BoundingBox
from labelformat.model.category import Category
from labelformat.model.image import Image
from labelformat.model.object_detection import (
    ImageObjectDetection,
    SingleObjectDetection,
)
from PIL import Image as PILImage
from sqlmodel import Session

from lightly_studio.core import add_samples
from lightly_studio.models.image import ImageCreate
from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers import caption_resolver, image_resolver
from tests.helpers_resolvers import create_dataset


def test_load_into_dataset_from_paths(db_session: Session, tmp_path: Path) -> None:
    # Arrange
    dataset = create_dataset(db_session)
    image_paths = [str(tmp_path / "image1.jpg")]
    PILImage.new("RGB", (100, 100)).save(image_paths[0])

    # Act
    sample_ids = add_samples.load_into_dataset_from_paths(
        session=db_session,
        dataset_id=dataset.dataset_id,
        image_paths=image_paths,
    )

    # Assert
    samples = image_resolver.get_all_by_dataset_id(
        session=db_session, dataset_id=dataset.dataset_id
    ).samples
    assert len(samples) == 1

    assert samples[0].sample_id == sample_ids[0]
    assert samples[0].dataset_id == dataset.dataset_id
    assert samples[0].file_name == "image1.jpg"
    assert samples[0].file_path_abs == str(image_paths[0])
    assert samples[0].width == 100
    assert samples[0].height == 100


def test_load_into_dataset_from_labelformat(db_session: Session, tmp_path: Path) -> None:
    # Arrange
    dataset = create_dataset(db_session)
    PILImage.new("RGB", (100, 200)).save(tmp_path / "image.jpg")
    label_input = _get_labelformat_input(filename="image.jpg")

    sample_ids = add_samples.load_into_dataset_from_labelformat(
        session=db_session,
        dataset_id=dataset.dataset_id,
        input_labels=label_input,
        images_path=tmp_path,
    )

    # Assert samples
    samples = image_resolver.get_all_by_dataset_id(
        session=db_session, dataset_id=dataset.dataset_id
    ).samples
    assert len(samples) == 1

    assert samples[0].sample_id == sample_ids[0]
    assert samples[0].dataset_id == dataset.dataset_id
    assert samples[0].file_name == "image.jpg"
    assert samples[0].file_path_abs == str((tmp_path / "image.jpg").absolute())
    assert samples[0].width == 100
    assert samples[0].height == 200

    # Assert annotations
    anns = samples[0].annotations
    assert len(anns) == 1
    assert anns[0].annotation_label.annotation_label_name == "dog"
    assert anns[0].object_detection_details is not None
    assert anns[0].object_detection_details.x == 10.0
    assert anns[0].object_detection_details.y == 20.0
    assert anns[0].object_detection_details.width == 20.0
    assert anns[0].object_detection_details.height == 20.0


def test_load_into_dataset_from_coco_captions(db_session: Session, tmp_path: Path) -> None:
    # Arrange
    dataset = create_dataset(db_session)

    # Create and save the coco json file containing the captions
    annotations_path = tmp_path / "annotations.json"
    _get_captions_input(annotations_path=annotations_path)

    _ = add_samples.load_into_dataset_from_coco_captions(
        session=db_session,
        dataset_id=dataset.dataset_id,
        annotations_json=annotations_path,
        images_path=tmp_path,
    )

    # Assert samples
    samples = image_resolver.get_all_by_dataset_id(
        session=db_session, dataset_id=dataset.dataset_id
    ).samples
    samples = sorted(samples, key=lambda sample: sample.file_path_abs)
    assert len(samples) == 2

    assert samples[0].dataset_id == dataset.dataset_id
    assert samples[0].file_name == "image1.jpg"
    assert samples[0].file_path_abs == str((tmp_path / "image1.jpg").absolute())
    assert samples[0].width == 640
    assert samples[0].height == 480

    assert samples[1].dataset_id == dataset.dataset_id
    assert samples[1].file_name == "image2.jpg"
    assert samples[1].file_path_abs == str((tmp_path / "image2.jpg").absolute())
    assert samples[1].width == 640
    assert samples[1].height == 480

    # Assert captions
    captions_result = caption_resolver.get_all(session=db_session, dataset_id=dataset.dataset_id)
    assert len(captions_result.captions) == 3
    assert captions_result.total_count == 3
    assert captions_result.next_cursor is None
    # Collect all the filename x caption pairs and assert they are as expected
    assert {
        (c.sample.sample_id, c.text)
        for c in captions_result.captions
        if isinstance(c.sample, SampleTable)
    } == {
        (samples[0].sample_id, "Caption 1 of image 1"),
        (samples[0].sample_id, "Caption 2 of image 1"),
        (samples[1].sample_id, "Caption 1 of image 2"),
    }


def test_create_batch_samples(db_session: Session) -> None:
    dataset = create_dataset(db_session)
    dataset_id = dataset.dataset_id

    # First batch: two new samples
    batch1 = [
        ImageCreate(
            file_path_abs="/path/to/image_0.png",
            file_name="image_0.png",
            width=100,
            height=200,
        ),
        ImageCreate(
            file_path_abs="/path/to/image_1.png",
            file_name="image_1.png",
            width=100,
            height=200,
        ),
    ]
    new_path_to_id, existing_paths = add_samples._create_batch_samples(
        session=db_session, dataset_id=dataset_id, samples=batch1
    )
    assert len(new_path_to_id) == 2
    assert len(existing_paths) == 0
    assert set(new_path_to_id.keys()) == {"/path/to/image_0.png", "/path/to/image_1.png"}

    # Check that the sample id mapping matches the database
    db_image_0 = image_resolver.get_by_id(
        session=db_session, dataset_id=dataset_id, sample_id=new_path_to_id["/path/to/image_0.png"]
    )
    db_image_1 = image_resolver.get_by_id(
        session=db_session, dataset_id=dataset_id, sample_id=new_path_to_id["/path/to/image_1.png"]
    )
    assert db_image_0 is not None
    assert db_image_0.file_path_abs == "/path/to/image_0.png"
    assert db_image_1 is not None
    assert db_image_1.file_path_abs == "/path/to/image_1.png"

    # Second batch: one existing, one new sample
    batch2 = [
        # existing - only file_path_abs matters
        ImageCreate(
            file_path_abs="/path/to/image_0.png",
            file_name="xxx.png",
            width=999,
            height=999,
        ),
        # new
        ImageCreate(
            file_path_abs="/path/to/image_2.png",
            file_name="image_2.png",
            width=100,
            height=200,
        ),
    ]

    new_path_to_id, existing_paths = add_samples._create_batch_samples(
        session=db_session, dataset_id=dataset_id, samples=batch2
    )
    assert len(new_path_to_id) == 1
    assert len(existing_paths) == 1
    assert list(new_path_to_id.keys()) == ["/path/to/image_2.png"]
    assert existing_paths == ["/path/to/image_0.png"]


def test_create_label_map(db_session: Session) -> None:
    # Test the creation of new labels and re-use of existing labels
    label_input = _get_labelformat_input(filename="image.jpg", category_names=["dog", "cat"])

    label_map_1 = add_samples._create_label_map(
        session=db_session,
        input_labels=label_input,
    )

    label_input_2 = _get_labelformat_input(
        filename="image.jpg", category_names=["dog", "cat", "bird"]
    )

    label_map_2 = add_samples._create_label_map(
        session=db_session,
        input_labels=label_input_2,
    )

    assert len(label_map_1) == 2  # dog and cat
    assert len(label_map_2) == 3  # dog, cat and bird

    # Compare label IDs for:
    assert label_map_2[0] == label_map_1[0]  # dog exists already
    assert label_map_2[1] == label_map_1[1]  # cat exists already
    assert label_map_2[2] not in label_map_1.values()  # bird is new


def _get_labelformat_input(
    filename: str = "image.jpg", category_names: list[str] | None = None
) -> LabelformatObjectDetectionInput:
    """Creates a LabelformatObjectDetectionInput for testing.

    Args:
        filename: The name of the image file.
        category_names: The names of the categories. Default: ["dog", "cat"].

    Returns:
        A LabelformatObjectDetectionInput object for testing.
    """
    if not category_names:
        category_names = ["dog", "cat"]

    categories = [
        Category(id=i, name=category_name) for i, category_name in enumerate(category_names)
    ]
    image = Image(id=0, filename=filename, width=100, height=200)
    objects = [
        SingleObjectDetection(
            category=categories[0],
            box=BoundingBox(xmin=10.0, ymin=20.0, xmax=30.0, ymax=40.0),
        ),
    ]

    return LabelformatObjectDetectionInput(
        categories=categories,
        images=[image],
        labels=[ImageObjectDetection(image=image, objects=objects)],
    )


def _get_captions_input(annotations_path: Path) -> None:
    """Creates a coco caption json and saves it for testing.

    Args:
        annotations_path: The path of the annotation json file.
    """
    coco_caption_dict = {
        "images": [
            {"id": 1, "file_name": "image1.jpg", "width": 640, "height": 480},
            {"id": 2, "file_name": "image2.jpg", "width": 640, "height": 480},
        ],
        "annotations": [
            {
                "id": 1,
                "image_id": 1,
                "caption": "Caption 1 of image 1",
            },
            {
                "id": 2,
                "image_id": 1,
                "caption": "Caption 2 of image 1",
            },
            {
                "id": 3,
                "image_id": 2,
                "caption": "Caption 1 of image 2",
            },
        ],
    }
    annotations_path.write_text(json.dumps(coco_caption_dict))
