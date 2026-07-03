from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import yaml
from numpy.typing import NDArray
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


def _create_sample_images(image_paths: list[Path]) -> None:
    for image_path in image_paths:
        image_path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (10, 10)).save(image_path)


def _create_mask(mask_path: Path, mask: NDArray[np.uint8]) -> None:
    mask_path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(mask).save(mask_path)


def _setup_dataset_with_images(tmp_path: Path, file_names: list[str]) -> tuple[ImageDataset, Path]:
    images_path = tmp_path / "images"
    images_path.mkdir()
    _create_sample_images([images_path / fn for fn in file_names])
    dataset = ImageDataset.create(name="test_dataset")
    dataset.add_images_from_path(path=images_path, embed=False)
    return dataset, images_path


class TestDataset:
    def test_add_annotations_from_coco__appends_to_existing_images(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        dataset, images_path = _setup_dataset_with_images(tmp_path, ["image1.jpg", "image2.jpg"])
        annotations_path = tmp_path / "annotations.json"
        annotations_path.write_text(json.dumps(_coco_dict_with(["image1.jpg", "image2.jpg"])))

        dataset.add_annotations_from_coco(
            annotations_json=annotations_path,
            images_root=images_path,
            annotation_source="ground_truth",
        )

        result = annotation_resolver.get_all_by_collection_name(
            session=dataset.session,
            collection_name="ground_truth",
            parent_collection_id=dataset.collection_id,
        )
        assert len(result.annotations) == 2

        # The annotation source is readable on each annotation.
        sample_annotations = [a for sample in dataset for a in sample.annotations]
        assert len(sample_annotations) == 2
        assert all(a.annotation_source == "ground_truth" for a in sample_annotations)

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

    def test_add_annotations_from_coco__same_annotation_source_appends(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        dataset, images_path = _setup_dataset_with_images(tmp_path, ["image1.jpg", "image2.jpg"])
        first_path = tmp_path / "first.json"
        first_path.write_text(json.dumps(_coco_dict_with(["image1.jpg"])))
        second_path = tmp_path / "second.json"
        second_path.write_text(json.dumps(_coco_dict_with(["image2.jpg"])))

        dataset.add_annotations_from_coco(
            annotations_json=first_path, images_root=images_path, annotation_source="gt"
        )
        dataset.add_annotations_from_coco(
            annotations_json=second_path, images_root=images_path, annotation_source="gt"
        )

        result = annotation_resolver.get_all_by_collection_name(
            session=dataset.session,
            collection_name="gt",
            parent_collection_id=dataset.collection_id,
        )
        assert len(result.annotations) == 2

    def test_add_annotations_from_coco__different_annotation_sources_separate_collections(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        dataset, images_path = _setup_dataset_with_images(tmp_path, ["image1.jpg"])
        annotations_path = tmp_path / "annotations.json"
        annotations_path.write_text(json.dumps(_coco_dict_with(["image1.jpg"])))

        dataset.add_annotations_from_coco(
            annotations_json=annotations_path, images_root=images_path, annotation_source="gt"
        )
        dataset.add_annotations_from_coco(
            annotations_json=annotations_path, images_root=images_path, annotation_source="model_A"
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
        annotations_path.write_text(json.dumps(_coco_dict_with(["image1.jpg", "missing.jpg"])))

        with caplog.at_level(logging.WARNING):
            dataset.add_annotations_from_coco(
                annotations_json=annotations_path, images_root=images_path, annotation_source="gt"
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

    def test_add_annotations_from_coco__no_matching_images_creates_no_annotation_source(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        # With embed_annotations defaulting to True, an import that matches no images (e.g. a
        # wrong images_root) must not leave behind an empty annotation source via the embed path.
        dataset, _ = _setup_dataset_with_images(tmp_path, ["image1.jpg"])
        annotations_path = tmp_path / "annotations.json"
        annotations_path.write_text(json.dumps(_coco_dict_with(["image1.jpg"])))

        dataset.add_annotations_from_coco(
            annotations_json=annotations_path,
            images_root=tmp_path / "wrong_root",
            annotation_source="gt",
        )

        assert (
            collection_resolver.get_by_name(
                session=dataset.session, name="gt", parent_collection_id=dataset.collection_id
            )
            is None
        )

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
            annotation_source="seg",
            annotation_type=AnnotationType.SEGMENTATION_MASK,
        )

        result = annotation_resolver.get_all_by_collection_name(
            session=dataset.session,
            collection_name="seg",
            parent_collection_id=dataset.collection_id,
        )
        assert len(result.annotations) == 1

    def test_add_annotations_from_yolo__loads_split_annotations(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        yaml_path = tmp_path / "data.yaml"
        yaml_path.write_text(
            yaml.dump(
                {"train": "../train/images", "val": "../val/images", "nc": 1, "names": ["class_0"]}
            )
        )
        images_path = tmp_path / "train" / "images"
        labels_path = tmp_path / "train" / "labels"
        labels_path.mkdir(parents=True, exist_ok=True)
        _create_sample_images([images_path / "image1.jpg", images_path / "image2.jpg"])
        for fn in ("image1.txt", "image2.txt"):
            (labels_path / fn).write_text("0 0.5 0.5 0.4 0.4\n")

        dataset = ImageDataset.create(name="test_dataset")
        dataset.add_images_from_path(path=images_path, embed=False)
        dataset.add_annotations_from_yolo(
            data_yaml=yaml_path, annotation_source="model_A", input_split="train"
        )

        result = annotation_resolver.get_all_by_collection_name(
            session=dataset.session,
            collection_name="model_A",
            parent_collection_id=dataset.collection_id,
        )
        assert len(result.annotations) == 2

    def test_add_annotations_from_pascal_voc_segmentations__appends_to_existing_images(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        dataset, images_path = _setup_dataset_with_images(tmp_path, ["image1.jpg", "image2.jpg"])
        masks_path = tmp_path / "masks"
        # image1 contains both background and "cat" pixels -> 2 annotations.
        mask1 = np.zeros((10, 10), dtype=np.uint8)
        mask1[0, 0] = 1
        _create_mask(masks_path / "image1.png", mask1)
        # image2 contains only background -> 1 annotation.
        _create_mask(masks_path / "image2.png", np.zeros((10, 10), dtype=np.uint8))

        dataset.add_annotations_from_pascal_voc_segmentations(
            masks_path=masks_path,
            images_root=images_path,
            class_id_to_name={0: "bg", 1: "cat"},
            annotation_source="ground_truth",
        )

        result = annotation_resolver.get_all_by_collection_name(
            session=dataset.session,
            collection_name="ground_truth",
            parent_collection_id=dataset.collection_id,
        )
        assert len(result.annotations) == 3

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

    def test_add_annotations_from_pascal_voc_segmentations__warns_on_missing_images(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        # Only image1 is added to the dataset.
        images_path = tmp_path / "images"
        images_path.mkdir()
        _create_sample_images([images_path / "image1.jpg"])
        dataset = ImageDataset.create(name="test_dataset")
        dataset.add_images_from_path(path=images_path, embed=False)

        # image2 exists on disk with a mask but was never added to the dataset.
        _create_sample_images([images_path / "image2.jpg"])
        masks_path = tmp_path / "masks"
        _create_mask(masks_path / "image1.png", np.zeros((10, 10), dtype=np.uint8))
        _create_mask(masks_path / "image2.png", np.zeros((10, 10), dtype=np.uint8))

        with caplog.at_level(logging.WARNING):
            dataset.add_annotations_from_pascal_voc_segmentations(
                masks_path=masks_path,
                images_root=images_path,
                class_id_to_name={0: "bg"},
                annotation_source="gt",
            )

        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert any(
            "skipped 1 annotation" in r.getMessage() and "image2.jpg" in r.getMessage()
            for r in warnings
        )

        result = annotation_resolver.get_all_by_collection_name(
            session=dataset.session,
            collection_name="gt",
            parent_collection_id=dataset.collection_id,
        )
        assert len(result.annotations) == 1
