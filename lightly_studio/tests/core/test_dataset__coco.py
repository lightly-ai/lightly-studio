from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest
from labelformat.types import ParseError
from PIL import Image

from lightly_studio import Dataset
from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.annotation.object_detection import ObjectDetectionAnnotationTable


def get_coco_annotation_dict_valid() -> dict[str, Any]:
    return {
        "images": [
            {"id": 1, "file_name": "image1.jpg", "width": 640, "height": 480},
            {"id": 2, "file_name": "image2.jpg", "width": 640, "height": 480},
        ],
        "annotations": [
            {
                "id": 1,
                "image_id": 1,
                "category_id": 1,
                "bbox": [100, 100, 200, 200],
                "area": 40000,
                "iscrowd": 0,
                "segmentation": [[100, 100, 100, 200, 200, 200]],
            },
            {
                "id": 2,
                "image_id": 2,
                "category_id": 2,
                "bbox": [150, 150, 250, 250],
                "area": 62500,
                "iscrowd": 0,
                "segmentation": [[150, 150, 150, 250, 250, 250]],
            },
        ],
        "categories": [{"id": 1, "name": "cat"}, {"id": 2, "name": "dog"}],
    }


class TestDataset:
    def test_add_samples_from_coco__details_valid(
        self,
        patch_dataset: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        annotations_path = tmp_path / "annotations.json"
        annotations_path.write_text(json.dumps(get_coco_annotation_dict_valid()))
        images_path = _create_valid_samples(tmp_path)

        # Run the test
        dataset = Dataset.create(name="test_dataset")
        dataset.add_samples_from_coco(
            annotations_json=annotations_path,
            images_path=images_path,
            annotation_type=AnnotationType.OBJECT_DETECTION,
        )
        assert dataset.name == "test_dataset"
        samples = list(dataset)
        samples = sorted(samples, key=lambda sample: sample.file_path_abs)

        assert len(samples) == 2
        assert {s.file_name for s in samples} == {"image1.jpg", "image2.jpg"}
        assert all(
            len(s.inner.sample.embeddings) == 1 for s in samples
        )  # Embeddings should be generated

        # Verify the first sample and annotation
        bbox = samples[0].inner.sample.annotations[0].object_detection_details
        annotation = samples[0].inner.sample.annotations[0].annotation_label
        assert isinstance(bbox, ObjectDetectionAnnotationTable)
        assert bbox.height == 200.0
        assert bbox.width == 200.0
        assert bbox.x == 100.0
        assert bbox.y == 100.0
        assert annotation.annotation_label_name == "cat"

        # Verify the second sample and annotation
        bbox = samples[1].inner.sample.annotations[0].object_detection_details
        annotation = samples[1].inner.sample.annotations[0].annotation_label
        assert isinstance(bbox, ObjectDetectionAnnotationTable)
        assert bbox.height == 250.0
        assert bbox.width == 250.0
        assert bbox.x == 150.0
        assert bbox.y == 150.0
        assert annotation.annotation_label_name == "dog"

    def test_add_samples_from_coco__valid_bbox(
        self,
        patch_dataset: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        annotations_path = tmp_path / "annotations.json"
        annotations_path.write_text(json.dumps(get_coco_annotation_dict_valid()))
        images_path = _create_valid_samples(tmp_path)

        dataset = Dataset.create(name="test_dataset")
        dataset.add_samples_from_coco(
            annotations_json=annotations_path,
            images_path=images_path,
            annotation_type=AnnotationType.OBJECT_DETECTION,
        )
        assert len(list(dataset)) == 2

    def test_add_samples_from_coco__valid_insseg(
        self,
        patch_dataset: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        annotations_path = tmp_path / "annotations.json"
        annotations_path.write_text(json.dumps(get_coco_annotation_dict_valid()))
        images_path = _create_valid_samples(tmp_path)

        dataset = Dataset.create(name="test_dataset")
        dataset.add_samples_from_coco(
            annotations_json=annotations_path,
            images_path=images_path,
            annotation_type=AnnotationType.INSTANCE_SEGMENTATION,
        )
        assert len(list(dataset)) == 2

    def test_add_samples_from_coco__invalid_annotation_arg(
        self,
        patch_dataset: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        annotations_path = tmp_path / "annotations.json"
        annotations_path.write_text(json.dumps(get_coco_annotation_dict_valid()))
        images_path = _create_valid_samples(tmp_path)

        dataset = Dataset.create(name="test_dataset")
        with pytest.raises(ValueError, match="Invalid annotation type: None"):
            dataset.add_samples_from_coco(
                annotations_json=annotations_path,
                images_path=images_path,
                annotation_type=None,  # type: ignore[arg-type]
            )

    def test_add_samples_from_coco__broken_structure(
        self,
        patch_dataset: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        coco_annotation_dict_broken_struct = {
            "images": [
                {"id": 1, "file_name": "image1.jpg", "width": 640, "height": 480},
                {"id": 2, "file_name": "image2.jpg", "width": 640, "height": 480},
            ],
        }
        annotations_path = tmp_path / "annotations.json"
        annotations_path.write_text(json.dumps(coco_annotation_dict_broken_struct))
        images_path = _create_valid_samples(tmp_path)

        dataset = Dataset.create(name="test_dataset")
        with pytest.raises(KeyError, match="'categories'"):
            dataset.add_samples_from_coco(
                annotations_json=annotations_path,
                images_path=images_path,
                annotation_type=AnnotationType.OBJECT_DETECTION,
            )

    def test_add_samples_from_coco__broken_categories(
        self,
        patch_dataset: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        coco_annotation_dict_broken_categories = get_coco_annotation_dict_valid()
        coco_annotation_dict_broken_categories["categories"] = [
            {"id": 1, "name": "cat"},
            {"id": 3, "name": "dog"},
        ]
        annotations_path = tmp_path / "annotations.json"
        annotations_path.write_text(json.dumps(coco_annotation_dict_broken_categories))
        images_path = _create_valid_samples(tmp_path)

        dataset = Dataset.create(name="test_dataset")
        with pytest.raises(KeyError, match="2"):
            dataset.add_samples_from_coco(
                annotations_json=annotations_path,
                images_path=images_path,
                annotation_type=AnnotationType.OBJECT_DETECTION,
            )

    def test_add_samples_from_coco__broken_image(
        self,
        patch_dataset: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        coco_annotation_dict_broken_image = get_coco_annotation_dict_valid()
        coco_annotation_dict_broken_image["images"][1]["id"] = 3

        annotations_path = tmp_path / "annotations.json"
        annotations_path.write_text(json.dumps(coco_annotation_dict_broken_image))
        images_path = _create_valid_samples(tmp_path)

        dataset = Dataset.create(name="test_dataset")
        with pytest.raises(KeyError, match="2"):
            dataset.add_samples_from_coco(
                annotations_json=annotations_path,
                images_path=images_path,
                annotation_type=AnnotationType.OBJECT_DETECTION,
            )

    def test_add_samples_from_coco__bbox_on_broken_seg(
        self,
        patch_dataset: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        coco_annotation_dict_broken_seg = get_coco_annotation_dict_valid()
        coco_annotation_dict_broken_seg["annotations"][0]["segmentation"] = [
            [100, 100, 100, 200, 200]
        ]  # 5 instead of 6

        annotations_path = tmp_path / "annotations.json"
        annotations_path.write_text(json.dumps(coco_annotation_dict_broken_seg))
        images_path = _create_valid_samples(tmp_path)

        dataset = Dataset.create(name="test_dataset")
        dataset.add_samples_from_coco(
            annotations_json=annotations_path,
            images_path=images_path,
            annotation_type=AnnotationType.OBJECT_DETECTION,
        )
        assert len(list(dataset)) == 2

    def test_add_samples_from_coco__bbox_on_broken_bbox(
        self,
        patch_dataset: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        coco_annotation_dict_broken_bbox = get_coco_annotation_dict_valid()
        coco_annotation_dict_broken_bbox["annotations"][0]["bbox"] = [100, 100, 200]  # 3 instead 4

        annotations_path = tmp_path / "annotations.json"
        annotations_path.write_text(json.dumps(coco_annotation_dict_broken_bbox))
        images_path = _create_valid_samples(tmp_path)

        dataset = Dataset.create(name="test_dataset")
        with pytest.raises(IndexError):
            dataset.add_samples_from_coco(
                annotations_json=annotations_path,
                images_path=images_path,
                annotation_type=AnnotationType.OBJECT_DETECTION,
            )

    def test_add_samples_from_coco__insseg_on_broken_seg(
        self,
        patch_dataset: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        coco_annotation_dict_broken_seg = get_coco_annotation_dict_valid()
        coco_annotation_dict_broken_seg["annotations"][0]["segmentation"] = [
            [100, 100, 100, 200, 200]
        ]  # 5 instead of 6

        annotations_path = tmp_path / "annotations.json"
        annotations_path.write_text(json.dumps(coco_annotation_dict_broken_seg))
        images_path = _create_valid_samples(tmp_path)

        dataset = Dataset.create(name="test_dataset")
        with pytest.raises(
            ParseError, match=re.escape("Invalid polygon with 5 points: [100, 100, 100, 200, 200]")
        ):
            dataset.add_samples_from_coco(
                annotations_json=annotations_path,
                images_path=images_path,
                annotation_type=AnnotationType.INSTANCE_SEGMENTATION,
            )

    def test_add_samples_from_coco__insseg_on_broken_bbox(
        self,
        patch_dataset: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        coco_annotation_dict_broken_bbox = get_coco_annotation_dict_valid()
        coco_annotation_dict_broken_bbox["annotations"][0]["bbox"] = [100, 100, 200]  # 3 instead 4

        annotations_path = tmp_path / "annotations.json"
        annotations_path.write_text(json.dumps(coco_annotation_dict_broken_bbox))
        images_path = _create_valid_samples(tmp_path)

        dataset = Dataset.create(name="test_dataset")
        dataset.add_samples_from_coco(
            annotations_json=annotations_path,
            images_path=images_path,
            annotation_type=AnnotationType.INSTANCE_SEGMENTATION,
        )
        assert len(list(dataset)) == 2

    def test_add_samples_from_coco__corrupted_json(
        self,
        patch_dataset: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        annotations_path = tmp_path / "annotations.json"
        annotations_path.write_text("{ this is not valid json }")
        images_path = _create_valid_samples(tmp_path)

        dataset = Dataset.create(name="test_dataset")
        with pytest.raises(json.JSONDecodeError):
            dataset.add_samples_from_coco(
                annotations_json=annotations_path,
                images_path=images_path,
                annotation_type=AnnotationType.OBJECT_DETECTION,
            )

    # TODO(Jonas 9/25): This case should be revisited in the future --> should warn and assert to 1
    def test_add_samples_from_coco__images_missing(
        self,
        patch_dataset: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        annotations_path = tmp_path / "annotations.json"
        annotations_path.write_text(json.dumps(get_coco_annotation_dict_valid()))
        images_path = tmp_path / "images"
        images_path.mkdir()
        _create_sample_images([images_path / "image1.jpg"])

        dataset = Dataset.create(name="test_dataset")
        dataset.add_samples_from_coco(
            annotations_json=annotations_path,
            images_path=images_path,
            annotation_type=AnnotationType.OBJECT_DETECTION,
        )
        assert len(list(dataset)) == 2

    # TODO(Jonas 9/25): This case should be revisited in the future --> should warn and assert to 0
    def test_add_samples_from_coco__non_dir(
        self,
        patch_dataset: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        annotations_path = tmp_path / "annotations.json"
        annotations_path.write_text(json.dumps(get_coco_annotation_dict_valid()))
        images_path = tmp_path / "images"

        dataset = Dataset.create(name="test_dataset")
        dataset.add_samples_from_coco(
            annotations_json=annotations_path,
            images_path=images_path,
            annotation_type=AnnotationType.OBJECT_DETECTION,
        )
        assert len(list(dataset)) == 2

    def test_add_samples_from_coco__annotations_json_no_file(
        self,
        patch_dataset: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        annotations_path = tmp_path / "annotations.json"
        images_path = tmp_path / "images"

        dataset = Dataset.create(name="test_dataset")
        with pytest.raises(
            FileNotFoundError, match=f"COCO annotations json file not found: '{annotations_path}'"
        ):
            dataset.add_samples_from_coco(
                annotations_json=annotations_path,
                images_path=images_path,
                annotation_type=AnnotationType.OBJECT_DETECTION,
            )

    def test_add_samples_from_coco__annotations_json_wrong_suffix(
        self,
        patch_dataset: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        annotations_path = tmp_path / "annotations.invalid_suffix"
        annotations_path.write_text(json.dumps(get_coco_annotation_dict_valid()))
        images_path = tmp_path / "images"

        dataset = Dataset.create(name="test_dataset")
        with pytest.raises(
            FileNotFoundError, match=f"COCO annotations json file not found: '{annotations_path}'"
        ):
            dataset.add_samples_from_coco(
                annotations_json=annotations_path,
                images_path=images_path,
                annotation_type=AnnotationType.OBJECT_DETECTION,
            )

    def test_add_samples_from_coco__dont_embed(
        self,
        patch_dataset: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        annotations_path = tmp_path / "annotations.json"
        annotations_path.write_text(json.dumps(get_coco_annotation_dict_valid()))
        images_path = _create_valid_samples(tmp_path)

        # Run the test
        dataset = Dataset.create(name="test_dataset")
        dataset.add_samples_from_coco(
            annotations_json=annotations_path,
            images_path=images_path,
            annotation_type=AnnotationType.OBJECT_DETECTION,
            embed=False,
        )

        # Check that an embedding was not created
        samples = list(dataset)
        assert all(len(sample.inner.sample.embeddings) == 0 for sample in samples)

    def test_add_samples_from_coco__tags_created_for_split(
        self,
        patch_dataset: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        annotations_path = tmp_path / "annotations.json"
        annotations_path.write_text(json.dumps(get_coco_annotation_dict_valid()))
        images_path = _create_valid_samples(tmp_path)

        dataset = Dataset.create()
        dataset.add_samples_from_coco(
            annotations_json=annotations_path,
            images_path=images_path,
            annotation_type=AnnotationType.OBJECT_DETECTION,
            split="train",
        )

        samples = list(dataset)
        assert len(samples) == 2

        assert all("train" in s.tags for s in samples)

    def test_add_samples_from_coco__no_tags_without_split(
        self,
        patch_dataset: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        annotations_path = tmp_path / "annotations.json"
        annotations_path.write_text(json.dumps(get_coco_annotation_dict_valid()))
        images_path = _create_valid_samples(tmp_path)

        dataset = Dataset.create()
        dataset.add_samples_from_coco(
            annotations_json=annotations_path,
            images_path=images_path,
            annotation_type=AnnotationType.OBJECT_DETECTION,
        )

        samples = list(dataset)
        assert len(samples) == 2

        assert len(samples[0].tags) == 0
        assert len(samples[1].tags) == 0


def _create_sample_images(image_paths: list[Path]) -> None:
    for image_path in image_paths:
        image_path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (10, 10)).save(image_path)


def _create_valid_samples(path: Path) -> Path:
    images_path = path / "images"
    images_path.mkdir()
    _create_sample_images(
        [
            images_path / "image1.jpg",
            images_path / "image2.jpg",
        ]
    )
    return images_path
