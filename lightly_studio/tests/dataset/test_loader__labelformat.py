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

from lightly_studio.dataset.loader import DatasetLoader
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.image import ImageTable


def get_input(
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


class TestDatasetLoader:
    @pytest.mark.parametrize("with_confidence", [True, False])
    def test_from_labelformat(
        self,
        patch_loader: None,  # noqa: ARG002
        with_confidence: bool,
    ) -> None:
        # Arrange
        dataset_name = f"test_dataset_{with_confidence}"
        image_folder_path = f"/fake/path/images_{with_confidence}"
        label_input = get_input(filename="image.jpg", with_confidence=with_confidence)

        loader = DatasetLoader()

        # Act
        dataset = loader.from_labelformat(
            input_labels=label_input,
            dataset_name=dataset_name,
            img_dir=image_folder_path,
        )
        assert dataset.name == dataset_name

        # Assert
        session = loader.session

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
