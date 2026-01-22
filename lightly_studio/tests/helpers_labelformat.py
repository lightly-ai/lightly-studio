from __future__ import annotations

from labelformat.formats.labelformat import LabelformatObjectDetectionInput
from labelformat.model.bounding_box import BoundingBox
from labelformat.model.category import Category
from labelformat.model.image import Image
from labelformat.model.object_detection import (
    ImageObjectDetection,
    SingleObjectDetection,
)


def get_labelformat_input_obj_det(
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
