from __future__ import annotations

import json
import logging
from pathlib import Path
from random import choice
from typing import Any

import pytest
import yaml
from labelformat.formats import COCOObjectDetectionInput
from PIL import Image

from lightly_studio import ImageDataset
from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import (
    annotation_collection_coverage_resolver,
    annotation_resolver,
    collection_resolver,
)


def _coco_dict_with(file_names: list[str]) -> dict[str, Any]:
    return {
        "images": [
            {"id": i + 1, "file_name": fn, "width": 640, "height": 480}
            for i, fn in enumerate(file_names)
        ],
        "annotations": [
            {
                "id": i + 1,
                "image_id": i + 1,
                "category_id": 1,
                "bbox": [10, 10, 20, 20],
                "area": 400,
                "iscrowd": 0,
                "segmentation": [[10, 10, 10, 30, 30, 30]],
            }
            for i in range(len(file_names))
        ],
        "categories": [{"id": 1, "name": "cat"}],
    }


def _yolo_yaml_dict() -> dict[str, Any]:
    return {
        "train": "../train/images",
        "val": "../val/images",
        "nc": 1,
        "names": ["class_0"],
    }


def _create_sample_images(image_paths: list[Path]) -> None:
    for image_path in image_paths:
        image_path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (10, 10)).save(image_path)


def _create_yolo_labels(label_paths: list[Path]) -> None:
    for label_path in label_paths:
        label_path.parent.mkdir(parents=True, exist_ok=True)
        label_path.write_text(f"{choice([0])} 0.5 0.5 0.4 0.4\n")


def _setup_dataset_with_images(
    tmp_path: Path, file_names: list[str]
) -> tuple[ImageDataset, Path]:
    images_path = tmp_path / "images"
    images_path.mkdir()
    _create_sample_images([images_path / fn for fn in file_names])
    dataset = ImageDataset.create(name="test_dataset")
    dataset.add_images_from_path(path=images_path, embed=False)
    return dataset, images_path


class TestDataset:
    def test_add_annotations_from_labelformat__generic_wrapper(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        dataset, images_path = _setup_dataset_with_images(tmp_path, ["image1.jpg"])
        annotations_path = tmp_path / "annotations.json"
        annotations_path.write_text(json.dumps(_coco_dict_with(["image1.jpg"])))
        label_input = COCOObjectDetectionInput(input_file=annotations_path)

        dataset.add_annotations_from_labelformat(
            input_labels=label_input,
            images_root=images_path,
            name="gt",
        )

        result = annotation_resolver.get_all_by_collection_name(
            session=dataset.session,
            collection_name="gt",
            parent_collection_id=dataset.collection_id,
        )
        assert len(result.annotations) == 1

    def test_add_annotations_from_coco__appends_to_existing_images(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        dataset, images_path = _setup_dataset_with_images(
            tmp_path, ["image1.jpg", "image2.jpg"]
        )
        annotations_path = tmp_path / "annotations.json"
        annotations_path.write_text(json.dumps(_coco_dict_with(["image1.jpg", "image2.jpg"])))

        dataset.add_annotations_from_coco(
            annotations_json=annotations_path,
            images_root=images_path,
            name="ground_truth",
        )

        result = annotation_resolver.get_all_by_collection_name(
            session=dataset.session,
            collection_name="ground_truth",
            parent_collection_id=dataset.collection_id,
        )
        assert len(result.annotations) == 2

        cov_id = collection_resolver.get_or_create_child_collection(
            session=dataset.session,
            collection_id=dataset.collection_id,
            sample_type=SampleType.ANNOTATION,
            name="ground_truth",
        )
        covered = set(
            annotation_collection_coverage_resolver.list_by_collection_id(
                session=dataset.session, annotation_collection_id=cov_id
            )
        )
        assert covered == {s.sample_id for s in dataset}

    def test_add_annotations_from_coco__same_name_appends(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        dataset, images_path = _setup_dataset_with_images(
            tmp_path, ["image1.jpg", "image2.jpg"]
        )
        first_path = tmp_path / "first.json"
        first_path.write_text(json.dumps(_coco_dict_with(["image1.jpg"])))
        second_path = tmp_path / "second.json"
        second_path.write_text(json.dumps(_coco_dict_with(["image2.jpg"])))

        dataset.add_annotations_from_coco(
            annotations_json=first_path, images_root=images_path, name="gt"
        )
        dataset.add_annotations_from_coco(
            annotations_json=second_path, images_root=images_path, name="gt"
        )

        result = annotation_resolver.get_all_by_collection_name(
            session=dataset.session,
            collection_name="gt",
            parent_collection_id=dataset.collection_id,
        )
        assert len(result.annotations) == 2

    def test_add_annotations_from_coco__different_names_separate_collections(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        dataset, images_path = _setup_dataset_with_images(tmp_path, ["image1.jpg"])
        annotations_path = tmp_path / "annotations.json"
        annotations_path.write_text(json.dumps(_coco_dict_with(["image1.jpg"])))

        dataset.add_annotations_from_coco(
            annotations_json=annotations_path, images_root=images_path, name="gt"
        )
        dataset.add_annotations_from_coco(
            annotations_json=annotations_path, images_root=images_path, name="model_A"
        )

        gt_result = annotation_resolver.get_all_by_collection_name(
            session=dataset.session,
            collection_name="gt",
            parent_collection_id=dataset.collection_id,
        )
        model_result = annotation_resolver.get_all_by_collection_name(
            session=dataset.session,
            collection_name="model_A",
            parent_collection_id=dataset.collection_id,
        )
        assert len(gt_result.annotations) == 1
        assert len(model_result.annotations) == 1
        gt_ids = {a.sample_id for a in gt_result.annotations}
        model_ids = {a.sample_id for a in model_result.annotations}
        assert gt_ids.isdisjoint(model_ids)

    def test_add_annotations_from_coco__warns_on_missing_images(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        dataset, images_path = _setup_dataset_with_images(tmp_path, ["image1.jpg"])
        annotations_path = tmp_path / "annotations.json"
        annotations_path.write_text(
            json.dumps(_coco_dict_with(["image1.jpg", "missing.jpg"]))
        )

        with caplog.at_level(logging.WARNING):
            dataset.add_annotations_from_coco(
                annotations_json=annotations_path, images_root=images_path, name="gt"
            )

        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert any(
            "skipped 1 annotation" in r.getMessage() and "missing.jpg" in r.getMessage()
            for r in warnings
        )

        result = annotation_resolver.get_all_by_collection_name(
            session=dataset.session,
            collection_name="gt",
            parent_collection_id=dataset.collection_id,
        )
        assert len(result.annotations) == 1

    def test_add_annotations_from_coco__segmentation_mask_annotation_type(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        dataset, images_path = _setup_dataset_with_images(tmp_path, ["image1.jpg"])
        annotations_path = tmp_path / "annotations.json"
        annotations_path.write_text(json.dumps(_coco_dict_with(["image1.jpg"])))

        dataset.add_annotations_from_coco(
            annotations_json=annotations_path,
            images_root=images_path,
            name="seg",
            annotation_type=AnnotationType.SEGMENTATION_MASK,
        )

        result = annotation_resolver.get_all_by_collection_name(
            session=dataset.session,
            collection_name="seg",
            parent_collection_id=dataset.collection_id,
        )
        assert len(result.annotations) == 1

    def test_add_annotations_from_coco__missing_json_raises(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        dataset, images_path = _setup_dataset_with_images(tmp_path, ["image1.jpg"])
        annotations_path = tmp_path / "does_not_exist.json"

        with pytest.raises(FileNotFoundError):
            dataset.add_annotations_from_coco(
                annotations_json=annotations_path, images_root=images_path, name="gt"
            )

    def test_add_annotations_from_yolo__loads_split_annotations(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        yaml_path = tmp_path / "data.yaml"
        yaml_path.write_text(yaml.dump(_yolo_yaml_dict()))
        images_path = tmp_path / "train" / "images"
        labels_path = tmp_path / "train" / "labels"
        _create_sample_images(
            [images_path / "image1.jpg", images_path / "image2.jpg"]
        )
        _create_yolo_labels(
            [labels_path / "image1.txt", labels_path / "image2.txt"]
        )

        dataset = ImageDataset.create(name="test_dataset")
        dataset.add_images_from_path(path=images_path, embed=False)
        dataset.add_annotations_from_yolo(
            data_yaml=yaml_path, name="model_A", input_split="train"
        )

        result = annotation_resolver.get_all_by_collection_name(
            session=dataset.session,
            collection_name="model_A",
            parent_collection_id=dataset.collection_id,
        )
        assert len(result.annotations) == 2

    def test_add_annotations_from_yolo__missing_yaml_raises(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        dataset, _ = _setup_dataset_with_images(tmp_path, ["image1.jpg"])
        yaml_path = tmp_path / "does_not_exist.yaml"

        with pytest.raises(FileNotFoundError):
            dataset.add_annotations_from_yolo(
                data_yaml=yaml_path, name="model_A", input_split="train"
            )
