from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from lightly_studio import ImageDataset
from lightly_studio.models.annotation.object_detection import ObjectDetectionAnnotationTable


class TestDataset:
    def test_add_samples_from_lightly(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        # Create the images
        images_path = tmp_path / "images"
        preds_path = tmp_path / "predictions"
        images_path.mkdir(parents=True, exist_ok=True)
        preds_path.mkdir(parents=True, exist_ok=True)
        _create_sample_images(
            image_paths=[
                images_path / "image1.jpg",
                images_path / "image2.jpg",
            ]
        )

        pred1_path = preds_path / "image1.json"
        pred1_path.write_text(json.dumps(_get_lightly_annotation_dict_1()))

        pred2_path = preds_path / "image2.json"
        pred2_path.write_text(json.dumps(_get_lightly_annotation_dict_2()))

        schema_path = preds_path / "schema.json"
        schema_path.write_text(json.dumps(_get_lightly_schema_dict()))

        # Run the test
        dataset = ImageDataset.create(name="test_dataset")
        dataset.add_samples_from_lightly(input_folder=preds_path)
        samples = list(dataset)
        samples = sorted(samples, key=lambda sample: sample.file_path_abs)

        assert len(samples) == 2
        assert {s.file_name for s in samples} == {"image1.jpg", "image2.jpg"}
        assert all(
            len(s.sample_table.embeddings) == 1 for s in samples
        )  # Embeddings should be generated

        # Verify the first sample and annotation
        bbox = samples[0].sample_table.annotations[0].object_detection_details
        annotation = samples[0].sample_table.annotations[0].annotation_label
        confidence = samples[0].sample_table.annotations[0].confidence
        assert isinstance(bbox, ObjectDetectionAnnotationTable)
        assert bbox.height == 200.0
        assert bbox.width == 200.0
        assert bbox.x == 100.0
        assert bbox.y == 100.0
        assert annotation.annotation_label_name == "cat"
        assert pytest.approx(confidence) == 0.75

        # Verify the second sample and annotation
        bbox = samples[1].sample_table.annotations[0].object_detection_details
        annotation = samples[1].sample_table.annotations[0].annotation_label
        confidence = samples[1].sample_table.annotations[0].confidence
        assert isinstance(bbox, ObjectDetectionAnnotationTable)
        assert bbox.height == 100.0
        assert bbox.width == 100.0
        assert bbox.x == 200.0
        assert bbox.y == 200.0
        assert annotation.annotation_label_name == "cat"
        assert pytest.approx(confidence) == 0.57

        bbox = samples[1].sample_table.annotations[1].object_detection_details
        annotation = samples[1].sample_table.annotations[1].annotation_label
        confidence = samples[1].sample_table.annotations[1].confidence
        assert isinstance(bbox, ObjectDetectionAnnotationTable)
        assert bbox.height == 10.0
        assert bbox.width == 10.0
        assert bbox.x == 20.0
        assert bbox.y == 20.0
        assert annotation.annotation_label_name == "dog"
        assert pytest.approx(confidence) == 0.99


def _create_sample_images(image_paths: list[Path]) -> None:
    for image_path in image_paths:
        image_path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (10, 10)).save(image_path)


def _get_lightly_annotation_dict_1() -> dict[str, Any]:
    return {
        "file_name": "image1.jpg",
        "predictions": [
            {"category_id": 1, "bbox": [100, 100, 200, 200], "score": 0.75},
        ],
    }


def _get_lightly_annotation_dict_2() -> dict[str, Any]:
    return {
        "file_name": "image2.jpg",
        "predictions": [
            {"category_id": 1, "bbox": [200, 200, 100, 100], "score": 0.57},
            {"category_id": 2, "bbox": [20, 20, 10, 10], "score": 0.99},
        ],
    }


def _get_lightly_schema_dict() -> dict[str, Any]:
    return {
        "task_type": "object-detection",
        "categories": [
            {"id": 1, "name": "cat"},
            {"id": 2, "name": "dog"},
        ],
    }
