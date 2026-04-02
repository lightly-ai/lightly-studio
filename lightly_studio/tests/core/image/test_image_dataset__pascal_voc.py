from __future__ import annotations

import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Union

import fsspec
import numpy as np
import pytest
from PIL import Image

from lightly_studio import ImageDataset
from lightly_studio.core.annotation.semantic_segmentation import SemanticSegmentationAnnotation

PascalVocPaths = tuple[Union[Path, str], Union[Path, str], str, str]
PascalVocPathsBuilder = Callable[[Path], PascalVocPaths]


def _build_pascal_voc_local_paths(tmp_path: Path) -> PascalVocPaths:
    images_path = tmp_path / "images"
    masks_path = tmp_path / "masks"
    images_path.mkdir(parents=True, exist_ok=True)
    masks_path.mkdir(parents=True, exist_ok=True)

    image1_path = images_path / "image1.jpg"
    image2_path = images_path / "image2.jpg"
    mask1_path = masks_path / "image1.png"
    mask2_path = masks_path / "image2.png"

    Image.new("RGB", (4, 3)).save(image1_path)
    Image.new("RGB", (3, 2)).save(image2_path)

    mask1 = np.array(
        [
            [0, 1, 0, 0],
            [1, 0, 0, 2],
            [0, 0, 2, 2],
        ],
        dtype=np.uint8,
    )
    Image.fromarray(mask1).save(mask1_path)

    mask2 = np.array(
        [
            [0, 0, 0],
            [0, 0, 0],
        ],
        dtype=np.uint8,
    )
    Image.fromarray(mask2).save(mask2_path)

    return images_path, masks_path, str(image1_path), str(image2_path)


def _build_pascal_voc_remote_paths(tmp_path: Path) -> PascalVocPaths:  # noqa: ARG001
    remote_root = f"memory://voc_remote_{uuid.uuid4().hex}"
    images_path = f"{remote_root}/JPEGImages"
    masks_path = f"{remote_root}/SegmentationClass"

    images_fs, images_fs_path = fsspec.core.url_to_fs(url=images_path)
    images_fs.makedirs(images_fs_path, exist_ok=True)
    masks_fs, masks_fs_path = fsspec.core.url_to_fs(url=masks_path)
    masks_fs.makedirs(masks_fs_path, exist_ok=True)

    image1_path = f"{images_path}/image1.jpg"
    image2_path = f"{images_path}/image2.jpg"
    mask1_path = f"{masks_path}/image1.png"
    mask2_path = f"{masks_path}/image2.png"

    with fsspec.open(image1_path, "wb") as image_file:
        Image.new("RGB", (4, 3)).save(image_file, format="JPEG")
    with fsspec.open(image2_path, "wb") as image_file:
        Image.new("RGB", (3, 2)).save(image_file, format="JPEG")

    mask1 = np.array(
        [
            [0, 1, 0, 0],
            [1, 0, 0, 2],
            [0, 0, 2, 2],
        ],
        dtype=np.uint8,
    )
    with fsspec.open(mask1_path, "wb") as mask_file:
        Image.fromarray(mask1).save(mask_file, format="PNG")

    mask2 = np.array(
        [
            [0, 0, 0],
            [0, 0, 0],
        ],
        dtype=np.uint8,
    )
    with fsspec.open(mask2_path, "wb") as mask_file:
        Image.fromarray(mask2).save(mask_file, format="PNG")

    return images_path, masks_path, image1_path, image2_path


class TestImageDataset:
    @pytest.mark.parametrize(
        "build_paths",
        [_build_pascal_voc_local_paths, _build_pascal_voc_remote_paths],
    )
    def test_add_samples_from_pascal_voc_segmentations(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
        build_paths: PascalVocPathsBuilder,
    ) -> None:
        images_path, masks_path, image1_path, image2_path = build_paths(tmp_path)

        # Run the test
        dataset = ImageDataset.create(name="test_dataset")
        dataset.add_samples_from_pascal_voc_segmentations(
            images_path=images_path,
            masks_path=masks_path,
            class_id_to_name={0: "bg", 1: "cat", 2: "dog", 3: "zebra"},
        )

        samples = list(dataset)
        samples = sorted(samples, key=lambda sample: sample.file_path_abs)

        assert len(samples) == 2
        assert [s.file_name for s in samples] == ["image1.jpg", "image2.jpg"]
        assert samples[0].file_path_abs == str(image1_path)
        assert samples[1].file_path_abs == str(image2_path)
        assert all(
            len(s.sample_table.embeddings) == 1 for s in samples
        )  # Embeddings should be generated

        # First sample
        annotations = sorted(samples[0].annotations, key=lambda ann: ann.label)

        # Verify the first annotation
        ann = annotations[0]
        assert isinstance(ann, SemanticSegmentationAnnotation)
        assert ann.label == "bg"
        assert ann.x == 0
        assert ann.y == 0
        assert ann.width == 4
        assert ann.height == 3
        assert ann.segmentation_mask == [0, 1, 1, 2, 1, 2, 1, 2, 2]

        # Verify the second annotation
        ann = annotations[1]
        assert isinstance(ann, SemanticSegmentationAnnotation)
        assert ann.label == "cat"
        assert ann.x == 0
        assert ann.y == 0
        assert ann.width == 2
        assert ann.height == 2
        assert ann.segmentation_mask == [1, 1, 2, 1, 7]

        # Verify the third annotation
        ann = annotations[2]
        assert isinstance(ann, SemanticSegmentationAnnotation)
        assert ann.label == "dog"
        assert ann.x == 2
        assert ann.y == 1
        assert ann.width == 2
        assert ann.height == 2
        assert ann.segmentation_mask == [7, 1, 2, 2]

        # Second sample
        assert len(samples[1].annotations) == 1
        ann = samples[1].annotations[0]
        assert isinstance(ann, SemanticSegmentationAnnotation)
        assert ann.label == "bg"
        assert ann.x == 0
        assert ann.y == 0
        assert ann.width == 3
        assert ann.height == 2
        assert ann.segmentation_mask == [0, 6]

    def test_add_samples_from_pascal_voc_segmentations__embed_split_flags(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        # Create the images
        images_path = tmp_path / "images"
        masks_path = tmp_path / "masks"
        images_path.mkdir(parents=True, exist_ok=True)
        masks_path.mkdir(parents=True, exist_ok=True)

        # Create an image and a mask
        Image.new("RGB", (3, 2)).save(images_path / "image.jpg")
        mask = np.zeros((2, 3), dtype=np.uint8)
        Image.fromarray(mask).save(masks_path / "image.png")

        # Run the test
        dataset = ImageDataset.create(name="test_dataset")
        dataset.add_samples_from_pascal_voc_segmentations(
            images_path=images_path,
            masks_path=masks_path,
            class_id_to_name={0: "bg"},
            split="test_split",
            embed=False,
        )

        samples = list(dataset)
        assert len(samples) == 1
        sample = samples[0]
        assert sample.file_name == "image.jpg"
        assert sample.tags == {"test_split"}
        assert sample.sample_table.embeddings == []
