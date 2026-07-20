from __future__ import annotations

import uuid
from collections.abc import Callable
from pathlib import Path

import fsspec
import numpy as np
import pytest
from PIL import Image

from lightly_studio import ImageDataset
from lightly_studio.core.annotation.segmentation_mask import SegmentationMaskAnnotation

PascalVocPaths = tuple[str, str, str, str]
PascalVocPathsBuilder = Callable[[Path], PascalVocPaths]


def _build_pascal_voc_paths(
    root_path: Path | str,
) -> PascalVocPaths:
    root_path_str = str(root_path)
    images_path = f"{root_path_str}/JPEGImages"
    masks_path = f"{root_path_str}/SegmentationClass"

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


def _build_pascal_voc_local_paths(tmp_path: Path) -> PascalVocPaths:
    return _build_pascal_voc_paths(root_path=tmp_path)


def _build_pascal_voc_remote_paths(tmp_path: Path) -> PascalVocPaths:  # noqa: ARG001
    remote_root = f"memory://voc_remote_{uuid.uuid4().hex}"
    return _build_pascal_voc_paths(root_path=remote_root)


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
        annotations = sorted(samples[0].annotations, key=lambda ann: ann.class_name)

        # Verify the first annotation
        ann = annotations[0]
        assert isinstance(ann, SegmentationMaskAnnotation)
        assert ann.class_name == "bg"
        assert ann.x == 0
        assert ann.y == 0
        assert ann.width == 4
        assert ann.height == 3
        assert ann.segmentation_mask == [0, 1, 1, 2, 1, 2, 1, 2, 2]

        # Verify the second annotation
        ann = annotations[1]
        assert isinstance(ann, SegmentationMaskAnnotation)
        assert ann.class_name == "cat"
        assert ann.x == 0
        assert ann.y == 0
        assert ann.width == 2
        assert ann.height == 2
        assert ann.segmentation_mask == [1, 1, 2, 1, 7]

        # Verify the third annotation
        ann = annotations[2]
        assert isinstance(ann, SegmentationMaskAnnotation)
        assert ann.class_name == "dog"
        assert ann.x == 2
        assert ann.y == 1
        assert ann.width == 2
        assert ann.height == 2
        assert ann.segmentation_mask == [7, 1, 2, 2]

        # Second sample
        assert len(samples[1].annotations) == 1
        ann = samples[1].annotations[0]
        assert isinstance(ann, SegmentationMaskAnnotation)
        assert ann.class_name == "bg"
        assert ann.x == 0
        assert ann.y == 0
        assert ann.width == 3
        assert ann.height == 2
        assert ann.segmentation_mask == [0, 6]

    def test_add_samples_from_pascal_voc_segmentations__limit(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        images_path, masks_path, image1_path, _ = _build_pascal_voc_local_paths(tmp_path)

        dataset = ImageDataset.create(name="test_dataset")
        dataset.add_samples_from_pascal_voc_segmentations(
            images_path=images_path,
            masks_path=masks_path,
            class_id_to_name={0: "bg", 1: "cat", 2: "dog"},
            limit=1,
        )

        samples = list(dataset)
        assert len(samples) == 1
        assert samples[0].file_path_abs == str(image1_path)

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

    def test_add_samples_from_pascal_voc_segmentations__records_broken_image(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        # Pascal VOC opens every image during the from_dirs folder scan (at construction), so a
        # broken image must be recorded as BROKEN and skipped instead of aborting the ingest.
        images_path = tmp_path / "JPEGImages"
        masks_path = tmp_path / "SegmentationClass"
        images_path.mkdir(parents=True, exist_ok=True)
        masks_path.mkdir(parents=True, exist_ok=True)

        # One good image with a matching mask.
        Image.new("RGB", (3, 2)).save(images_path / "good.jpg")
        Image.fromarray(np.zeros((2, 3), dtype=np.uint8)).save(masks_path / "good.png")

        # One broken image: present on disk but not decodable. It is dropped during the folder
        # scan before its mask is looked up, so no mask is needed.
        (images_path / "broken.jpg").write_bytes(b"not a real image")

        dataset = ImageDataset.create(name="test_dataset")
        with caplog.at_level("INFO", logger="lightly_studio.core.file_outcome_report"):
            dataset.add_samples_from_pascal_voc_segmentations(
                images_path=images_path,
                masks_path=masks_path,
                class_id_to_name={0: "bg"},
                embed=False,
            )

        # Only the readable image becomes a sample; the broken one is skipped, not created.
        samples = list(dataset)
        assert [sample.file_name for sample in samples] == ["good.jpg"]

        # The broken image is recorded in the end-of-run summary.
        assert "added=1" in caplog.text
        assert "broken=1" in caplog.text

    @pytest.mark.parametrize(
        ("image_state", "probe_added", "broken_count"),
        [
            ("healthy", True, 0),
            ("broken", False, 1),
            ("missing", False, 0),
        ],
    )
    def test_add_samples_from_pascal_voc_segmentations__image_matrix(  # noqa: PLR0913
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
        image_state: str,
        probe_added: bool,
        broken_count: int,
    ) -> None:
        # End-to-end coverage of a healthy/broken/missing image for Pascal VOC. The mask axis is
        # held valid on purpose: a missing mask raises at from_dirs construction and a broken
        # mask raises during get_labels, both by design and unchanged by this PR, so only the
        # image axis is exercised here. A guaranteed-healthy anchor pair keeps the run from
        # failing with AllInputFilesFailedError so each probe outcome is asserted in isolation.
        images_path = tmp_path / "JPEGImages"
        masks_path = tmp_path / "SegmentationClass"
        images_path.mkdir(parents=True, exist_ok=True)
        masks_path.mkdir(parents=True, exist_ok=True)

        # Anchor: a decodable image with a matching mask.
        Image.new("RGB", (3, 2)).save(images_path / "anchor.jpg")
        Image.fromarray(np.zeros((2, 3), dtype=np.uint8)).save(masks_path / "anchor.png")

        # Probe image (a broken image is dropped during the folder scan before its mask is
        # looked up, and a missing image is never scanned, so neither needs a mask).
        if image_state == "healthy":
            Image.new("RGB", (3, 2)).save(images_path / "probe.jpg")
            Image.fromarray(np.zeros((2, 3), dtype=np.uint8)).save(masks_path / "probe.png")
        elif image_state == "broken":
            (images_path / "probe.jpg").write_bytes(b"not a real image")
        # "missing": no probe image file is created.

        dataset = ImageDataset.create(name="test_dataset")
        with caplog.at_level("INFO", logger="lightly_studio.core.file_outcome_report"):
            dataset.add_samples_from_pascal_voc_segmentations(
                images_path=images_path,
                masks_path=masks_path,
                class_id_to_name={0: "bg"},
                embed=False,
            )

        names = {sample.file_name for sample in dataset}

        # The anchor is always added; the probe only when its image is readable.
        assert "anchor.jpg" in names
        assert ("probe.jpg" in names) == probe_added

        # A broken probe image is recorded BROKEN exactly once; other states record none.
        assert f"broken={broken_count}" in caplog.text
