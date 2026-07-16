from __future__ import annotations

from pathlib import Path
from random import choice
from typing import Any

import pytest
import yaml
from PIL import Image

from lightly_studio import ImageDataset
from lightly_studio.models.annotation.object_detection import ObjectDetectionAnnotationTable
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import (
    annotation_collection_coverage_resolver,
    collection_resolver,
)


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
        patch_collection: None,  # noqa: ARG002
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
        dataset = ImageDataset.create(name="test_dataset")
        dataset.add_samples_from_yolo(data_yaml=annotations_path, input_split="train")
        assert dataset.name == "test_dataset"
        samples = list(dataset)

        assert len(samples) == 2
        assert {s.file_name for s in samples} == {"image1.jpg", "image2.jpg"}
        assert all(
            len(s.sample_table.embeddings) == 1 for s in samples
        )  # Embeddings should be generated

        # Verify first annotation
        bbox = samples[0].sample_table.annotations[0].object_detection_details
        annotation = samples[0].sample_table.annotations[0].annotation_label
        assert isinstance(bbox, ObjectDetectionAnnotationTable)
        assert bbox.height == 4.0
        assert bbox.width == 4.0
        assert bbox.x == 3.0
        assert bbox.y == 3.0
        assert annotation.annotation_label_name in ("class_0", "class_1", "class_2")

        # Verify second annotation
        bbox = samples[1].sample_table.annotations[0].object_detection_details
        annotation = samples[1].sample_table.annotations[0].annotation_label
        assert isinstance(bbox, ObjectDetectionAnnotationTable)
        assert bbox.height == 4.0
        assert bbox.width == 4.0
        assert bbox.x == 3.0
        assert bbox.y == 3.0
        assert annotation.annotation_label_name in ("class_0", "class_1", "class_2")

    def test_add_samples_from_yolo__valid(
        self,
        patch_collection: None,  # noqa: ARG002
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

        dataset = ImageDataset.create(name="test_dataset")
        dataset.add_samples_from_yolo(data_yaml=yaml_path, input_split="train")
        assert len(list(dataset)) == 2

    def test_add_samples_from_yolo__valid_test_split(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        yaml_path = tmp_path / "data.yaml"
        yaml_path.write_text(yaml.dump(get_yolo_yaml_dict_valid()))

        images_path_train = tmp_path / "train" / "images"
        labels_path_train = tmp_path / "train" / "labels"
        _create_images(images_path_train)
        _create_labels(labels_path_train)

        dataset = ImageDataset.create(name="test_dataset")
        dataset.add_samples_from_yolo(data_yaml=yaml_path, input_split="test")
        assert len(list(dataset)) == 0

    def test_add_samples_from_yolo__tags_created_for_split(
        self,
        patch_collection: None,  # noqa: ARG002
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

        dataset = ImageDataset.create()
        dataset.add_samples_from_yolo(data_yaml=yaml_path, input_split="train")

        samples = list(dataset)
        assert len(samples) == 2
        assert all("train" in sample.tags for sample in samples)

    def test_add_samples_from_yolo__all_splits_loaded(
        self,
        patch_collection: None,  # noqa: ARG002
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

        dataset = ImageDataset.create()
        # Load all splits (default behavior when input_split=None)
        dataset.add_samples_from_yolo(data_yaml=yaml_path)

        samples = list(dataset)
        assert len(samples) == 4
        assert samples[0].tags == {"train"}
        assert samples[1].tags == {"train"}
        assert samples[2].tags == {"val"}
        assert samples[3].tags == {"val"}

    def test_add_samples_from_yolo__limit_across_splits(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        """``limit`` caps the total number of samples across all processed splits."""
        yaml_path = tmp_path / "data.yaml"
        yaml_path.write_text(yaml.dump(get_yolo_yaml_dict_valid()))

        # Two images per split (train + val) => 4 available in total.
        _create_images(tmp_path / "train" / "images")
        _create_labels(tmp_path / "train" / "labels")
        _create_images(tmp_path / "val" / "images")
        _create_labels(tmp_path / "val" / "labels")

        dataset = ImageDataset.create(name="test_dataset")
        # limit=3 should load both train images, then only one val image.
        dataset.add_samples_from_yolo(data_yaml=yaml_path, limit=3)

        assert len(list(dataset)) == 3

    @pytest.mark.parametrize("limit", [0, -1])
    def test_add_samples_from_yolo__invalid_limit(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
        limit: int,
    ) -> None:
        yaml_path = tmp_path / "data.yaml"
        yaml_path.write_text(yaml.dump(get_yolo_yaml_dict_valid()))

        dataset = ImageDataset.create(name="test_dataset")
        with pytest.raises(ValueError, match=r"limit must be greater than 0"):
            dataset.add_samples_from_yolo(data_yaml=yaml_path, input_split="train", limit=limit)

    # TODO(Jonas 9/25): We might want a warning here --> since folder does not exist
    def test_add_samples_from_yolo__labels_folder_non_exist(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        yaml_path = tmp_path / "data.yaml"
        yaml_path.write_text(yaml.dump(get_yolo_yaml_dict_valid()))

        images_path_train = tmp_path / "train" / "images"
        _create_images(images_path_train)

        dataset = ImageDataset.create(name="test_dataset")
        dataset.add_samples_from_yolo(data_yaml=yaml_path, input_split="train")
        assert len(list(dataset)) == 0

    # TODO(Jonas 9/25): We might want a warning here --> since label files don't match images
    def test_add_samples_from_yolo__labels_not_match_images(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        yaml_path = tmp_path / "data.yaml"
        yaml_path.write_text(yaml.dump(get_yolo_yaml_dict_valid()))

        images_path_train = tmp_path / "train" / "images"
        labels_path_train = tmp_path / "train" / "labels"
        _create_images(images_path_train)  # creates image1.jpg and image2.jpg
        _create_labels(labels_path_train, label_file_names=["image1", "image4"])

        dataset = ImageDataset.create(name="test_dataset")
        dataset.add_samples_from_yolo(data_yaml=yaml_path, input_split="train")
        assert len(list(dataset)) == 1

    # TODO(Jonas 9/25): We might want a warning here --> since annotations don't match categories
    def test_add_samples_from_yolo__anno_not_match_cat(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        yaml_path = tmp_path / "data.yaml"
        yaml_path.write_text(yaml.dump(get_yolo_yaml_dict_valid()))

        images_path_train = tmp_path / "train" / "images"
        labels_path_train = tmp_path / "train" / "labels"
        _create_images(images_path_train)
        _create_labels(labels_path_train, class_sample_pool=[3, 4])

        dataset = ImageDataset.create(name="test_dataset")
        dataset.add_samples_from_yolo(data_yaml=yaml_path, input_split="train")
        samples = list(dataset)
        assert len(samples) == 2

        for sample in samples:
            assert len(sample.sample_table.annotations) == 0

    # TODO(Jonas 9/25): We might want a warning here --> since no dir exists
    def test_add_samples_from_yolo__train_path_invalid(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        yolo_yaml_dict_path_broken = get_yolo_yaml_dict_valid()
        yolo_yaml_dict_path_broken["train"] = "../invalid_path/images"

        yaml_path = tmp_path / "data.yaml"
        yaml_path.write_text(yaml.dump(yolo_yaml_dict_path_broken))

        dataset = ImageDataset.create(name="test_dataset")
        dataset.add_samples_from_yolo(data_yaml=yaml_path, input_split="train")
        assert len(list(dataset)) == 0

    def test_add_samples_from_yolo__categories_missing_yaml(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        yolo_yaml_dict_categories_missing = get_yolo_yaml_dict_valid()
        yolo_yaml_dict_categories_missing.pop("names")
        yolo_yaml_dict_categories_missing.pop("nc")

        yaml_path = tmp_path / "data.yaml"
        yaml_path.write_text(yaml.dump(yolo_yaml_dict_categories_missing))

        dataset = ImageDataset.create(name="test_dataset")
        with pytest.raises(KeyError):
            dataset.add_samples_from_yolo(data_yaml=yaml_path, input_split="train")

    def test_add_samples_from_yolo__yaml_corrupt(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        yaml_path = tmp_path / "data.yaml"
        yaml_path.write_text("corrupted yaml content")

        dataset = ImageDataset.create(name="test_dataset")
        with pytest.raises(
            ValueError, match=f"Split 'train' not found in config file '{yaml_path}'"
        ):
            dataset.add_samples_from_yolo(data_yaml=yaml_path, input_split="train")

    def test_add_samples_from_yolo__unknown_split(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        yaml_path = tmp_path / "data.yaml"
        yaml_path.write_text(yaml.dump(get_yolo_yaml_dict_valid()))

        dataset = ImageDataset.create(name="test_dataset")
        with pytest.raises(
            ValueError, match=f"Split 'training' not found in config file '{yaml_path}'"
        ):
            dataset.add_samples_from_yolo(data_yaml=yaml_path, input_split="training")

    def test_add_samples_from_yolo__splits_missing_yaml(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        yaml_path = tmp_path / "data.yaml"
        yaml_path.write_text(yaml.dump({"nc": 1, "names": ["class_0"]}))

        dataset = ImageDataset.create()
        with pytest.raises(ValueError, match=f"No splits found in config file '{yaml_path}'"):
            dataset.add_samples_from_yolo(data_yaml=yaml_path)

    def test_add_samples_from_yolo__yaml_not_a_file(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        yaml_path = tmp_path / "data.yaml"

        dataset = ImageDataset.create(name="test_dataset")
        with pytest.raises(
            FileNotFoundError, match=f"YOLO data yaml file not found: '{yaml_path}'"
        ):
            dataset.add_samples_from_yolo(data_yaml=yaml_path, input_split="train")

    def test_add_samples_from_yolo__yaml_wrong_suffix(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        yaml_path = tmp_path / "data.invalid_suffix"
        yaml_path.write_text(yaml.dump(get_yolo_yaml_dict_valid()))

        dataset = ImageDataset.create(name="test_dataset")
        with pytest.raises(
            FileNotFoundError, match=f"YOLO data yaml file not found: '{yaml_path}'"
        ):
            dataset.add_samples_from_yolo(data_yaml=yaml_path, input_split="train")

    def test_add_samples_from_yolo__dont_embed(
        self,
        patch_collection: None,  # noqa: ARG002
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
        dataset = ImageDataset.create(name="test_dataset")
        dataset.add_samples_from_yolo(data_yaml=annotations_path, input_split="train", embed=False)

        # No embedding should be created
        samples = list(dataset)
        assert len(samples) == 1
        assert len(samples[0].sample_table.embeddings) == 0

    def test_add_samples_from_yolo__records_broken_image(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        # YOLO opens every image to read its dimensions during the get_images()/get_labels()
        # folder scans, so a broken image must be recorded as BROKEN and skipped instead of
        # aborting the ingest.
        annotations_path = tmp_path / "data.yaml"
        annotations_path.write_text(yaml.dump(get_yolo_yaml_dict_valid()))

        images_path_train = tmp_path / "train" / "images"
        labels_path_train = tmp_path / "train" / "labels"
        _create_sample_images([images_path_train / "good.jpg"])
        _create_sample_labels([labels_path_train / "good.txt"])

        # A broken image: present on disk but not decodable, with a matching label file.
        (images_path_train / "broken.jpg").write_bytes(b"not a real image")
        _create_sample_labels([labels_path_train / "broken.txt"])

        dataset = ImageDataset.create(name="test_dataset")
        with caplog.at_level("INFO", logger="lightly_studio.core.file_outcome_report"):
            dataset.add_samples_from_yolo(
                data_yaml=annotations_path, input_split="train", embed=False
            )

        # Only the readable image becomes a sample; the broken one is skipped, not created.
        samples = list(dataset)
        assert [sample.file_name for sample in samples] == ["good.jpg"]

        # The broken image is recorded in the end-of-run summary.
        assert "added=1" in caplog.text
        assert "broken=1" in caplog.text

    @pytest.mark.parametrize(
        ("image_state", "annotation_state", "probe_added", "probe_annotations", "broken_count"),
        [
            # A decodable image with a valid label: added and annotated.
            ("healthy", "healthy", True, 1, 0),
            # A decodable image whose label content is malformed: added, but the unparsable
            # entries are dropped, so it carries no annotation.
            ("healthy", "broken", True, 0, 0),
            # A decodable image with no label file: get_labels() skips it, so it is never
            # offered for sample creation and no sample is added.
            ("healthy", "missing", False, 0, 0),
            # An undecodable image: recorded BROKEN and skipped during the folder scan,
            # regardless of its label state.
            ("broken", "healthy", False, 0, 1),
            ("broken", "broken", False, 0, 1),
            ("broken", "missing", False, 0, 1),
            # An image absent from the folder: never discovered by the scan, so its label (if
            # any) is a solitary label that YOLO ignores. Nothing is added or recorded.
            ("missing", "healthy", False, 0, 0),
            ("missing", "broken", False, 0, 0),
            ("missing", "missing", False, 0, 0),
        ],
    )
    def test_add_samples_from_yolo__image_x_annotation_matrix(  # noqa: PLR0913
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
        image_state: str,
        annotation_state: str,
        probe_added: bool,
        probe_annotations: int,
        broken_count: int,
    ) -> None:
        # End-to-end coverage of every combination of a healthy/broken/missing image with a
        # healthy/broken/missing annotation. A guaranteed-healthy "anchor" pair is always
        # present so the run never fails with AllInputFilesFailedError and each probe outcome
        # is asserted in isolation.
        annotations_path = tmp_path / "data.yaml"
        annotations_path.write_text(
            yaml.dump({"train": "../train/images", "nc": 1, "names": ["c"]})
        )

        images_path = tmp_path / "train" / "images"
        labels_path = tmp_path / "train" / "labels"
        images_path.mkdir(parents=True, exist_ok=True)
        labels_path.mkdir(parents=True, exist_ok=True)

        # Anchor: a decodable image with a single valid box.
        Image.new("RGB", (10, 10)).save(images_path / "anchor.jpg")
        (labels_path / "anchor.txt").write_text("0 0.5 0.5 0.4 0.4\n")

        # Probe image.
        if image_state == "healthy":
            Image.new("RGB", (10, 10)).save(images_path / "probe.jpg")
        elif image_state == "broken":
            (images_path / "probe.jpg").write_bytes(b"not a real image")
        # "missing": no probe image file is created.

        # Probe annotation.
        if annotation_state == "healthy":
            (labels_path / "probe.txt").write_text("0 0.5 0.5 0.4 0.4\n")
        elif annotation_state == "broken":
            # Wrong field count: parsed, warned about, and dropped, leaving no annotation.
            (labels_path / "probe.txt").write_text("not a valid yolo label line\n")
        # "missing": no probe label file is created.

        dataset = ImageDataset.create(name="test_dataset")
        with caplog.at_level("INFO", logger="lightly_studio.core.file_outcome_report"):
            dataset.add_samples_from_yolo(
                data_yaml=annotations_path, input_split="train", embed=False
            )

        samples = list(dataset)
        names = {sample.file_name for sample in samples}

        # The anchor is always added; the probe is added only in the expected combinations.
        assert "anchor.jpg" in names
        assert ("probe.jpg" in names) == probe_added

        # The anchor contributes one annotation; the probe adds its expected count on top.
        total_annotations = sum(len(sample.sample_table.annotations) for sample in samples)
        assert total_annotations == 1 + probe_annotations

        # A broken probe image is recorded BROKEN exactly once; other states record none.
        assert f"broken={broken_count}" in caplog.text

    def test_add_samples_from_yolo__coverage_includes_empty_label_file(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        """Coverage must include images with empty label files (zero-detection case)."""
        (tmp_path / "data.yaml").write_text(yaml.dump(get_yolo_yaml_dict_valid()))
        images_path = tmp_path / "train" / "images"
        labels_path = tmp_path / "train" / "labels"
        images_path.mkdir(parents=True, exist_ok=True)
        labels_path.mkdir(parents=True, exist_ok=True)
        _create_sample_images([images_path / "image1.jpg", images_path / "image2.jpg"])
        _create_sample_labels([labels_path / "image1.txt"])
        (labels_path / "image2.txt").write_text("")

        dataset = ImageDataset.create(name="test_dataset")
        dataset.add_samples_from_yolo(
            data_yaml=tmp_path / "data.yaml", input_split="train", embed=False
        )

        samples = list(dataset)
        # Verify both images were loaded (including empty-label image2).
        assert len(samples) == 2, f"Expected 2 samples, got {len(samples)}"
        image1_sample = next((s for s in samples if "image1" in s.file_path_abs), None)
        image2_sample = next((s for s in samples if "image2" in s.file_path_abs), None)
        assert image1_sample is not None, "image1 must be loaded"
        assert image2_sample is not None, "image2 (empty label) must be loaded"
        assert len(image2_sample.sample_table.annotations) == 0

        cov_id = collection_resolver.get_or_create_child_collection(
            session=dataset.session,
            collection_id=dataset.collection_id,
            sample_type=SampleType.ANNOTATION,
        )
        covered = set(
            annotation_collection_coverage_resolver.list_by_collection_id(
                session=dataset.session, annotation_collection_id=cov_id
            )
        )
        assert covered == {image1_sample.sample_id, image2_sample.sample_id}


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
