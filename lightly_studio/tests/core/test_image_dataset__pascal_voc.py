from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from lightly_studio import ImageDataset
from lightly_studio.models.annotation.object_detection import ObjectDetectionAnnotationTable


class TestImageDataset:
    def test_add_samples_from_pascalvoc(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        # Create the images
        images_path = tmp_path / "images"
        masks_path = tmp_path / "masks"
        images_path.mkdir(parents=True, exist_ok=True)
        masks_path.mkdir(parents=True, exist_ok=True)

        # Create images
        Image.new("RGB", (3, 4)).save(images_path / "image1.jpg")
        Image.new("RGB", (2, 3)).save(images_path / "image2.jpg")

        # Create masks
        mask1 = np.array(
            [
                [0, 1, 0, 0],
                [1, 0, 0, 2],
                [0, 0, 2, 2],
            ],
            dtype=np.uint8,
        )
        Image.fromarray(mask1, mode='L').save(masks_path / "image1.png")
        mask2 = np.array(
            [
                [0, 0, 0],
                [0, 0, 0],
            ],
            dtype=np.uint8,
        )
        Image.fromarray(mask2, mode='L').save(masks_path / "image2.png")


        # Run the test
        dataset = ImageDataset.create(name="test_dataset")
        dataset.add_samples_from_pascal_voc(
            images_path=images_path,
            masks_path=masks_path,
            class_id_to_name={0: "bg", 1: "cat", 2: "dog", 3: "zebra"},
        )

        samples = list(dataset)
        samples = sorted(samples, key=lambda sample: sample.file_path_abs)

        assert len(samples) == 2
        assert [s.file_name for s in samples] == ["image1.jpg", "image2.jpg"]
        assert all(
            len(s.sample_table.embeddings) == 1 for s in samples
        )  # Embeddings should be generated

        # Verify the first sample and annotation
        annotations = sorted(samples[0].annotations, key=lambda ann: ann.label())
        # confidence = samples[0].sample_table.annotations[0].confidence
        # assert isinstance(bbox, ObjectDetectionAnnotationTable)
        # assert bbox.height == 200.0
        # assert bbox.width == 200.0
        # assert bbox.x == 100.0
        # assert bbox.y == 100.0
        # assert annotation.annotation_label_name == "cat"
        # assert pytest.approx(confidence) == 0.75

        # # Verify the second sample and annotation
        # bbox = samples[1].sample_table.annotations[0].object_detection_details
        # annotation = samples[1].sample_table.annotations[0].annotation_label
        # confidence = samples[1].sample_table.annotations[0].confidence
        # assert isinstance(bbox, ObjectDetectionAnnotationTable)
        # assert bbox.height == 100.0
        # assert bbox.width == 100.0
        # assert bbox.x == 200.0
        # assert bbox.y == 200.0
        # assert annotation.annotation_label_name == "cat"
        # assert pytest.approx(confidence) == 0.57

        # bbox = samples[1].sample_table.annotations[1].object_detection_details
        # annotation = samples[1].sample_table.annotations[1].annotation_label
        # confidence = samples[1].sample_table.annotations[1].confidence
        # assert isinstance(bbox, ObjectDetectionAnnotationTable)
        # assert bbox.height == 10.0
        # assert bbox.width == 10.0
        # assert bbox.x == 20.0
        # assert bbox.y == 20.0
        # assert annotation.annotation_label_name == "dog"
        # assert pytest.approx(confidence) == 0.99

