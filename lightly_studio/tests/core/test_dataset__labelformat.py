from __future__ import annotations

from pathlib import Path

import pytest
from labelformat.formats.labelformat import LabelformatObjectDetectionInput
from labelformat.model.bounding_box import BoundingBox
from labelformat.model.category import Category
from labelformat.model.image import Image
from labelformat.model.object_detection import (
    ImageObjectDetection,
    SingleObjectDetection,
)
from sqlmodel import select

from lightly_studio import Dataset
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.image import ImageTable


class TestDataset:
    @pytest.mark.parametrize("with_confidence", [True, False])
    def test_from_labelformat(
        self,
        patch_dataset: None,  # noqa: ARG002
        with_confidence: bool,
    ) -> None:
        # Arrange
        dataset_name = f"test_dataset_{with_confidence}"
        image_folder_path = f"/fake/path/images_{with_confidence}"
        label_input = _get_input(filename="image.jpg", with_confidence=with_confidence)

        dataset = Dataset.create(name=dataset_name)
        dataset.add_samples_from_labelformat(
            input_labels=label_input,
            images_path=image_folder_path,
        )
        assert dataset.name == dataset_name

        # Assert
        session = dataset.session

        # Check labels
        labels = session.exec(select(AnnotationLabelTable)).all()
        assert len(labels) == 3
        label_names = {lbl.annotation_label_name for lbl in labels}
        assert label_names == {"cat", "dog", "cow"}

        # Check sample
        sample = session.exec(select(ImageTable)).first()
        assert sample is not None
        assert sample.file_name == "image.jpg"
        assert sample.width == 100
        assert sample.height == 200
        assert sample.file_path_abs == str(Path(image_folder_path).absolute() / "image.jpg")
        assert len(sample.sample.embeddings) == 1  # An embedding should be created

        # Check annotations
        annotations = session.exec(select(AnnotationBaseTable)).all()
        assert len(annotations) == 2

        # Find dog and cat annotations by their label
        dog_annotation = next(
            (ann for ann in annotations if ann.annotation_label.annotation_label_name == "dog"),
        )
        cat_annotation = next(
            (ann for ann in annotations if ann.annotation_label.annotation_label_name == "cat"),
        )

        dog_details = dog_annotation.object_detection_details

        assert dog_details is not None
        # Check dog annotation
        assert dog_details.x == pytest.approx(10.0)
        assert dog_details.y == pytest.approx(20.0)
        assert dog_details.width == pytest.approx(20.0)  # 30 - 10 = 20
        assert dog_details.height == pytest.approx(20.0)  # 40 - 20 = 20
        assert dog_annotation.confidence == (pytest.approx(0.4) if with_confidence else None)

        cat_details = cat_annotation.object_detection_details
        # Check cat annotation
        assert cat_details is not None
        assert cat_details.x == pytest.approx(50.0)
        assert cat_details.y == pytest.approx(60.0)
        assert cat_details.width == pytest.approx(20.0)  # 70 - 50 = 20
        assert cat_details.height == pytest.approx(20.0)  # 80 - 60 = 20
        assert cat_annotation.confidence == (pytest.approx(0.8) if with_confidence else None)

    def test_from_labelformat__duplication(
        self,
        patch_dataset: None,  # noqa: ARG002
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        # Arrange
        dataset_name = "test_dataset"
        image_folder_path = "/fake/path/images"
        label_input = _get_input(filename="image.jpg")

        dataset = Dataset.create(name=dataset_name)
        dataset.add_samples_from_labelformat(
            input_labels=label_input,
            images_path=image_folder_path,
        )

        # Adding a new one
        label_input = _get_input(filename="new.jpg")
        dataset.add_samples_from_labelformat(
            input_labels=label_input,
            images_path=image_folder_path,
        )

        assert len(list(dataset)) == 2

        # Adding a duplicate
        label_input = _get_input(filename="image.jpg")
        dataset.add_samples_from_labelformat(
            input_labels=label_input,
            images_path=image_folder_path,
        )

        assert len(list(dataset)) == 2

        captured = capsys.readouterr()
        assert "Added 0 out of 1 new samples to the dataset." in captured.out
        assert "Examples of paths that were not added:  /fake/path/images/image.jpg" in captured.out

    def test_from_labelformat__annotations_synced_images(
        self,
        patch_dataset: None,  # noqa: ARG002
    ) -> None:
        # This test is to ensure that the images and annotations stay in sync while loading.
        # In the past, the image file paths got processed separately causing non matching pairs

        # Arrange
        dataset_name = "test_dataset"
        image_folder_path = "/fake/path/images"
        label_input = _get_input_multi()
        # image1: 020.jpg -> cat
        # image2: 001.jpg -> dog

        dataset = Dataset.create(name=dataset_name)
        dataset.add_samples_from_labelformat(
            input_labels=label_input,
            images_path=image_folder_path,
        )

        samples = list(dataset)
        samples = sorted(samples, key=lambda sample: sample.file_path_abs)

        # Verify first image and annotation
        annotation = samples[0].inner.sample.annotations[0].annotation_label
        assert samples[0].file_name == "001.jpg"
        assert annotation.annotation_label_name == "dog"

        # Verify first image and annotation
        annotation = samples[1].inner.sample.annotations[0].annotation_label
        assert samples[1].file_name == "020.jpg"
        assert annotation.annotation_label_name == "cat"

    def test_from_labelformat__dont_embed(
        self,
        patch_dataset: None,  # noqa: ARG002
    ) -> None:
        dataset_name = "test_dataset"
        image_folder_path = "/fake/path/images"
        label_input = _get_input(filename="image.jpg")

        dataset = Dataset.create(name=dataset_name)
        dataset.add_samples_from_labelformat(
            input_labels=label_input,
            images_path=image_folder_path,
            embed=False,
        )

        # Check that an embedding was not created
        samples = dataset.query().to_list()
        assert len(samples) == 1
        assert len(samples[0].inner.sample.embeddings) == 0


def _get_input(
    filename: str = "image.jpg", with_confidence: bool = False
) -> LabelformatObjectDetectionInput:
    """Creates a LabelformatObjectDetectionInput for testing.

    Args:
        filename: The name of the image file.
        with_confidence: Whether to include confidence scores.

    Returns:
        A LabelformatObjectDetectionInput object for testing.
    """
    categories = [
        Category(id=0, name="cat"),
        Category(id=1, name="dog"),
        Category(id=2, name="cow"),
    ]
    image = Image(id=0, filename=filename, width=100, height=200)

    objects = [
        SingleObjectDetection(
            category=categories[1],
            box=BoundingBox(xmin=10.0, ymin=20.0, xmax=30.0, ymax=40.0),
            confidence=0.4 if with_confidence else None,
        ),
        SingleObjectDetection(
            category=categories[0],
            box=BoundingBox(xmin=50.0, ymin=60.0, xmax=70.0, ymax=80.0),
            confidence=0.8 if with_confidence else None,
        ),
    ]

    return LabelformatObjectDetectionInput(
        categories=categories,
        images=[image],
        labels=[ImageObjectDetection(image=image, objects=objects)],
    )


def _get_input_multi() -> LabelformatObjectDetectionInput:
    """Creates a LabelformatObjectDetectionInput for testing.

    Returns:
        A LabelformatObjectDetectionInput object for testing.
    """
    categories = [
        Category(id=0, name="cat"),
        Category(id=1, name="dog"),
    ]
    image1 = Image(id=0, filename="020.jpg", width=100, height=200)
    image2 = Image(id=1, filename="001.jpg", width=100, height=200)

    objects1 = [
        SingleObjectDetection(
            category=categories[0],
            box=BoundingBox(xmin=50.0, ymin=60.0, xmax=70.0, ymax=80.0),
            confidence=None,
        ),
    ]

    objects2 = [
        SingleObjectDetection(
            category=categories[1],
            box=BoundingBox(xmin=10.0, ymin=20.0, xmax=30.0, ymax=40.0),
            confidence=None,
        ),
    ]

    return LabelformatObjectDetectionInput(
        categories=categories,
        images=[image1, image2],
        labels=[
            ImageObjectDetection(image=image1, objects=objects1),
            ImageObjectDetection(image=image2, objects=objects2),
        ],
    )
