"""Tests for the image-specific export wiring in `image_dataset_export`.

The sample-type-agnostic export format logic is tested in the `test_dataset_export__*.py`
files. Here we only cover what is image-specific: the `image_sample_to_image` mapping and that
`ImageDataset.export()` uses it and forwards the query.
"""

from __future__ import annotations

import json
from pathlib import Path

from lightly_studio.core.dataset_query import ImageSampleField
from lightly_studio.core.image.image_dataset import ImageDataset
from lightly_studio.export import image_dataset_export
from tests.helpers_resolvers import ImageStub, create_images


class TestImageDatasetExport:
    def test_export__forwards_query_and_maps_image_samples(
        self,
        tmp_path: Path,
        patch_collection: None,  # noqa: ARG002
    ) -> None:
        """Tests that `ImageDataset.export(query)` forwards the query and maps image samples.

        The exported images are filtered by the query and referenced by their absolute path.
        """
        dataset = ImageDataset.create(name="test_dataset")
        create_images(
            db_session=dataset.session,
            collection_id=dataset.collection_id,
            images=[
                ImageStub(path="/abs/dir/image0.jpg", width=100, height=100),
                ImageStub(path="/abs/dir/image1.jpg", width=200, height=200),
            ],
        )

        output_json = tmp_path / "coco.json"
        query = dataset.query().match(ImageSampleField.height <= 100)
        dataset.export(query).to_coco_object_detections(output_json=output_json)

        with open(output_json) as f:
            coco_data = json.load(f)
        # Only the image matching the query is exported, referenced by its absolute path.
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
