from __future__ import annotations

from pathlib import Path
from random import choice
from typing import Any

import pytest
import yaml
from PIL import Image

from lightly_studio import Dataset
from lightly_studio.models.annotation.object_detection import ObjectDetectionAnnotationTable


def get_yolo_yaml_dict_valid() -> dict[str, Any]:
    return {
        "train": "../train/images",
        "val": "../val/images",
        "test": "../test/images",
        "nc": 3,
        "names": [
            "class_0",
            "class_1",
            "class_2",
        ],
    }


class TestDataset:
    def test_add_samples_from_yolo_details_valid(
        self,
        patch_dataset: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        annotations_path = tmp_path / "data.yaml"
        annotations_path.write_text(yaml.dump(get_yolo_yaml_dict_valid()))

        # Create the images
        images_path_train = tmp_path / "train" / "images"
        labels_path_train = tmp_path / "train" / "labels"
        images_path_train.mkdir(parents=True, exist_ok=True)
        labels_path_train.mkdir(parents=True, exist_ok=True)
        _create_sample_images(
            [
                images_path_train / "image1.jpg",
                images_path_train / "image2.jpg",
            ]
        )
        _create_sample_labels(
            [
                labels_path_train / "image1.txt",
                labels_path_train / "image2.txt",
            ]
        )

        # Run the test
        dataset = Dataset.create(name="test_dataset")
        dataset.add_samples_from_yolo(data_yaml=annotations_path, input_split="train")
        assert dataset.name == "test_dataset"
        samples = dataset._inner.get_samples()

        assert len(samples) == 2
        assert {s.file_name for s in samples} == {"image1.jpg", "image2.jpg"}
        assert all(len(s.sample.embeddings) == 1 for s in samples)  # Embeddings should be generated

        # Verify first annotation
        bbox = samples[0].sample.annotations[0].object_detection_details
        annotation = samples[0].sample.annotations[0].annotation_label
        assert isinstance(bbox, ObjectDetectionAnnotationTable)
        assert bbox.height == 4.0
        assert bbox.width == 4.0
        assert bbox.x == 3.0
        assert bbox.y == 3.0
        assert annotation.annotation_label_name in ("class_0", "class_1", "class_2")

        # Verify second annotation
        bbox = samples[1].sample.annotations[0].object_detection_details
        annotation = samples[1].sample.annotations[0].annotation_label
        assert isinstance(bbox, ObjectDetectionAnnotationTable)
        assert bbox.height == 4.0
        assert bbox.width == 4.0
        assert bbox.x == 3.0
        assert bbox.y == 3.0
        assert annotation.annotation_label_name in ("class_0", "class_1", "class_2")

    def test_add_samples_from_yolo__valid(
        self,
        patch_dataset: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        yaml_path = tmp_path / "data.yaml"
        yaml_path.write_text(yaml.dump(get_yolo_yaml_dict_valid()))

        images_path_train = tmp_path / "train" / "images"
        labels_path_train = tmp_path / "train" / "labels"
        _create_images(images_path_train)
        _create_labels(labels_path_train)

        images_path_val = tmp_path / "val" / "images"
        labels_path_val = tmp_path / "val" / "labels"
        _create_images(images_path_val)
        _create_labels(labels_path_val)

        dataset = Dataset.create(name="test_dataset")
        dataset.add_samples_from_yolo(data_yaml=yaml_path, input_split="train")
        assert len(dataset._inner.get_samples()) == 2

    def test_add_samples_from_yolo__valid_test_split(
        self,
        patch_dataset: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        yaml_path = tmp_path / "data.yaml"
        yaml_path.write_text(yaml.dump(get_yolo_yaml_dict_valid()))

        images_path_train = tmp_path / "train" / "images"
        labels_path_train = tmp_path / "train" / "labels"
        _create_images(images_path_train)
        _create_labels(labels_path_train)

        dataset = Dataset.create(name="test_dataset")
        dataset.add_samples_from_yolo(data_yaml=yaml_path, input_split="test")
        assert len(dataset._inner.get_samples()) == 0

    def test_add_samples_from_yolo__tags_created_for_split(
        self,
        patch_dataset: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        yaml_path = tmp_path / "data.yaml"
        yaml_path.write_text(yaml.dump(get_yolo_yaml_dict_valid()))

        images_path_train = tmp_path / "train" / "images"
        labels_path_train = tmp_path / "train" / "labels"
        _create_images(images_path_train)
        _create_labels(labels_path_train)

        images_path_val = tmp_path / "val" / "images"
        labels_path_val = tmp_path / "val" / "labels"
        _create_images(images_path_val)
        _create_labels(labels_path_val)

        dataset = Dataset.create()
        dataset.add_samples_from_yolo(data_yaml=yaml_path, input_split="train")

        samples = list(dataset)
        assert len(samples) == 2
        assert all("train" in sample.tags for sample in samples)

    def test_add_samples_from_yolo__all_splits_loaded(
        self,
        patch_dataset: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        yaml_path = tmp_path / "data.yaml"
        yaml_path.write_text(yaml.dump(get_yolo_yaml_dict_valid()))

        # Create train split
        images_path_train = tmp_path / "train" / "images"
        labels_path_train = tmp_path / "train" / "labels"
        _create_images(images_path_train)
        _create_labels(labels_path_train)

        # Create val split
        images_path_val = tmp_path / "val" / "images"
        labels_path_val = tmp_path / "val" / "labels"
        _create_images(images_path_val)
        _create_labels(labels_path_val)

        dataset = Dataset.create()
        # Load all splits (default behavior when input_split=None)
        dataset.add_samples_from_yolo(data_yaml=yaml_path)

        samples = list(dataset)
        assert len(samples) == 4
        assert samples[0].tags == {"train"}
        assert samples[1].tags == {"train"}
        assert samples[2].tags == {"val"}
        assert samples[3].tags == {"val"}

    # TODO(Jonas 9/25): We might want a warning here --> since folder does not exist
    def test_add_samples_from_yolo__labels_folder_non_exist(
        self,
        patch_dataset: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        yaml_path = tmp_path / "data.yaml"
        yaml_path.write_text(yaml.dump(get_yolo_yaml_dict_valid()))

        images_path_train = tmp_path / "train" / "images"
        _create_images(images_path_train)

        dataset = Dataset.create(name="test_dataset")
        dataset.add_samples_from_yolo(data_yaml=yaml_path, input_split="train")
        assert len(dataset._inner.get_samples()) == 0

    # TODO(Jonas 9/25): We might want a warning here --> since label files don't match images
    def test_add_samples_from_yolo__labels_not_match_images(
        self,
        patch_dataset: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        yaml_path = tmp_path / "data.yaml"
        yaml_path.write_text(yaml.dump(get_yolo_yaml_dict_valid()))

        images_path_train = tmp_path / "train" / "images"
        labels_path_train = tmp_path / "train" / "labels"
        _create_images(images_path_train)  # creates image1.jpg and image2.jpg
        _create_labels(labels_path_train, label_file_names=["image1", "image4"])

        dataset = Dataset.create(name="test_dataset")
        dataset.add_samples_from_yolo(data_yaml=yaml_path, input_split="train")
        assert len(dataset._inner.get_samples()) == 1

    # TODO(Jonas 9/25): We might want a warning here --> since annotations don't match categories
    def test_add_samples_from_yolo__anno_not_match_cat(
        self,
        patch_dataset: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        yaml_path = tmp_path / "data.yaml"
        yaml_path.write_text(yaml.dump(get_yolo_yaml_dict_valid()))

        images_path_train = tmp_path / "train" / "images"
        labels_path_train = tmp_path / "train" / "labels"
        _create_images(images_path_train)
        _create_labels(labels_path_train, class_sample_pool=[3, 4])

        dataset = Dataset.create(name="test_dataset")
        dataset.add_samples_from_yolo(data_yaml=yaml_path, input_split="train")
        samples = dataset._inner.get_samples()
        assert len(samples) == 2

        for sample in samples:
            assert len(sample.sample.annotations) == 0

    # TODO(Jonas 9/25): We might want a warning here --> since no dir exists
    def test_add_samples_from_yolo__train_path_invalid(
        self,
        patch_dataset: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        yolo_yaml_dict_path_broken = get_yolo_yaml_dict_valid()
        yolo_yaml_dict_path_broken["train"] = "../invalid_path/images"

        yaml_path = tmp_path / "data.yaml"
        yaml_path.write_text(yaml.dump(yolo_yaml_dict_path_broken))

        dataset = Dataset.create(name="test_dataset")
        dataset.add_samples_from_yolo(data_yaml=yaml_path, input_split="train")
        assert len(dataset._inner.get_samples()) == 0

    def test_add_samples_from_yolo__categories_missing_yaml(
        self,
        patch_dataset: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        yolo_yaml_dict_categories_missing = get_yolo_yaml_dict_valid()
        yolo_yaml_dict_categories_missing.pop("names")
        yolo_yaml_dict_categories_missing.pop("nc")

        yaml_path = tmp_path / "data.yaml"
        yaml_path.write_text(yaml.dump(yolo_yaml_dict_categories_missing))

        dataset = Dataset.create(name="test_dataset")
        with pytest.raises(KeyError):
            dataset.add_samples_from_yolo(data_yaml=yaml_path, input_split="train")

    def test_add_samples_from_yolo__yaml_corrupt(
        self,
        patch_dataset: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        yaml_path = tmp_path / "data.yaml"
        yaml_path.write_text("corrupted yaml content")

        dataset = Dataset.create(name="test_dataset")
        with pytest.raises(
            ValueError, match=f"Split 'train' not found in config file '{yaml_path}'"
        ):
            dataset.add_samples_from_yolo(data_yaml=yaml_path, input_split="train")

    def test_add_samples_from_yolo__unknown_split(
        self,
        patch_dataset: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        yaml_path = tmp_path / "data.yaml"
        yaml_path.write_text(yaml.dump(get_yolo_yaml_dict_valid()))

        dataset = Dataset.create(name="test_dataset")
        with pytest.raises(
            ValueError, match=f"Split 'training' not found in config file '{yaml_path}'"
        ):
            dataset.add_samples_from_yolo(data_yaml=yaml_path, input_split="training")

    def test_add_samples_from_yolo__splits_missing_yaml(
        self,
        patch_dataset: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        yaml_path = tmp_path / "data.yaml"
        yaml_path.write_text(yaml.dump({"nc": 1, "names": ["class_0"]}))

        dataset = Dataset.create()
        with pytest.raises(ValueError, match=f"No splits found in config file '{yaml_path}'"):
            dataset.add_samples_from_yolo(data_yaml=yaml_path)

    def test_add_samples_from_yolo__yaml_not_a_file(
        self,
        patch_dataset: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        yaml_path = tmp_path / "data.yaml"

        dataset = Dataset.create(name="test_dataset")
        with pytest.raises(
            FileNotFoundError, match=f"YOLO data yaml file not found: '{yaml_path}'"
        ):
            dataset.add_samples_from_yolo(data_yaml=yaml_path, input_split="train")

    def test_add_samples_from_yolo__yaml_wrong_suffix(
        self,
        patch_dataset: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        yaml_path = tmp_path / "data.invalid_suffix"
        yaml_path.write_text(yaml.dump(get_yolo_yaml_dict_valid()))

        dataset = Dataset.create(name="test_dataset")
        with pytest.raises(
            FileNotFoundError, match=f"YOLO data yaml file not found: '{yaml_path}'"
        ):
            dataset.add_samples_from_yolo(data_yaml=yaml_path, input_split="train")

    def test_add_samples_from_yolo__dont_embed(
        self,
        patch_dataset: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        annotations_path = tmp_path / "data.yaml"
        annotations_path.write_text(yaml.dump(get_yolo_yaml_dict_valid()))

        # Create the images
        images_path_train = tmp_path / "train" / "images"
        labels_path_train = tmp_path / "train" / "labels"
        images_path_train.mkdir(parents=True, exist_ok=True)
        labels_path_train.mkdir(parents=True, exist_ok=True)
        _create_sample_images([images_path_train / "image1.jpg"])
        _create_sample_labels([labels_path_train / "image1.txt"])

        # Run the test
        dataset = Dataset.create(name="test_dataset")
        dataset.add_samples_from_yolo(data_yaml=annotations_path, input_split="train", embed=False)

        # No embedding should be created
        samples = dataset._inner.get_samples()
        assert len(samples) == 1
        assert len(samples[0].sample.embeddings) == 0


def _create_sample_images(image_paths: list[Path]) -> None:
    for image_path in image_paths:
        image_path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (10, 10)).save(image_path)


def _create_sample_labels(
    label_paths: list[Path], class_sample_pool: list[int] | None = None
) -> None:
    if class_sample_pool is None:
        class_sample_pool = [0, 1, 2]
    for label_path in label_paths:
        label_path.parent.mkdir(parents=True, exist_ok=True)
        label_path.write_text(f"{choice(class_sample_pool)} 0.5 0.5 0.4 0.4\n")


def _create_images(images_path_train: Path) -> None:
    images_path_train.mkdir(parents=True, exist_ok=True)
    _create_sample_images(
        [
            images_path_train / "image1.jpg",
            images_path_train / "image2.jpg",
        ]
    )


def _create_labels(
    labels_path_train: Path,
    label_file_names: list[str] | None = None,
    class_sample_pool: list[int] | None = None,
) -> None:
    if label_file_names is None:
        label_file_names = ["image1", "image2"]
    if class_sample_pool is None:
        class_sample_pool = [0, 1, 2]
    labels_path_train.mkdir(parents=True, exist_ok=True)
    _create_sample_labels(
        [labels_path_train / f"{name}.txt" for name in label_file_names],
        class_sample_pool=class_sample_pool,
    )
