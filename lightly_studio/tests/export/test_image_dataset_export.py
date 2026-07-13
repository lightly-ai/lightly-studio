"""Tests for the image-specific export wiring in `image_dataset_export`.

The sample-type-agnostic export format logic is tested in `test_dataset_export.py`. Here we
only cover what is image-specific: the `image_sample_to_image` mapping and that
`ImageDatasetExport` binds it.
"""

from __future__ import annotations

import json
from pathlib import Path

from lightly_studio.core.image.image_dataset import ImageDataset
from lightly_studio.export import image_dataset_export
from tests.helpers_resolvers import ImageStub, create_images


class TestImageDatasetExport:
    def test_export__coco_uses_absolute_image_path(
        self,
        tmp_path: Path,
        patch_collection: None,  # noqa: ARG002
    ) -> None:
        """Tests that `ImageDataset.export()` maps image samples via `image_sample_to_image`."""
        dataset = ImageDataset.create(name="test_dataset")
        create_images(
            db_session=dataset.session,
            collection_id=dataset.collection_id,
            images=[ImageStub(path="/abs/dir/image0.jpg", width=100, height=100)],
        )

        output_json = tmp_path / "coco.json"
        dataset.export().to_coco_object_detections(output_json=output_json)

        with open(output_json) as f:
            coco_data = json.load(f)
        assert coco_data["images"] == [
            {"id": 0, "file_name": "/abs/dir/image0.jpg", "width": 100, "height": 100},
        ]


def test_image_sample_to_image__coco_uses_absolute_path(
    patch_collection: None,  # noqa: ARG001
) -> None:
    """COCO exports reference the absolute image path."""
    dataset = ImageDataset.create(name="test_dataset")
    create_images(
        db_session=dataset.session,
        collection_id=dataset.collection_id,
        images=[ImageStub(path="/abs/dir/image0.jpg", width=100, height=200)],
    )
    sample = next(iter(dataset))

    image = image_dataset_export.image_sample_to_image(
        sample=sample, image_id=7, use_relative_filename=False
    )

    assert image.id == 7
    assert image.filename == "/abs/dir/image0.jpg"
    assert image.width == 100
    assert image.height == 200


def test_image_sample_to_image__yolo_pascal_use_relative_name(
    patch_collection: None,  # noqa: ARG001
) -> None:
    """YOLO and Pascal VOC exports reference the relative file name."""
    dataset = ImageDataset.create(name="test_dataset")
    create_images(
        db_session=dataset.session,
        collection_id=dataset.collection_id,
        images=[ImageStub(path="/abs/dir/image0.jpg", width=100, height=200)],
    )
    sample = next(iter(dataset))

    image = image_dataset_export.image_sample_to_image(
        sample=sample, image_id=7, use_relative_filename=True
    )

    assert image.id == 7
    assert image.filename == "image0.jpg"
    assert image.width == 100
    assert image.height == 200
