from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from lightly_studio import ImageDataset
from lightly_studio.metadata import compute_image_quality


class TestDataset:
    def test_compute_image_quality_metadata(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        Image.new("RGB", (16, 8), color=(100, 100, 100)).save(tmp_path / "gray.png")

        dataset = ImageDataset.create(name="test_dataset")
        dataset.add_images_from_path(path=tmp_path, embed=False)

        dataset.compute_image_quality_metadata()

        (sample,) = dataset.query().to_list()
        assert sample.metadata["brightness"] == pytest.approx(100.0)
        assert sample.metadata["contrast"] == 0.0
        assert sample.metadata["sharpness"] == 0.0
        assert sample.metadata["entropy"] == 0.0
        assert sample.metadata["aspect_ratio"] == 2.0
        assert (
            sample.metadata["image_quality_version"]
            == compute_image_quality.IMAGE_QUALITY_METRICS_VERSION
        )

    def test_compute_image_quality_metadata__broken_image_gets_no_values(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        Image.new("RGB", (8, 8), color=(0, 0, 0)).save(tmp_path / "dark.png")
        broken_path = tmp_path / "broken.jpg"
        Image.new("RGB", (8, 8)).save(broken_path)

        dataset = ImageDataset.create(name="test_dataset")
        dataset.add_images_from_path(path=tmp_path, embed=False)
        # Corrupt the file after ingest so the decode fails at metric time.
        broken_path.write_bytes(b"not an image")

        dataset.compute_image_quality_metadata()

        samples = {s.file_name: s for s in dataset.query().to_list()}
        assert samples["dark.png"].metadata["brightness"] == 0.0
        # A broken file must not receive a zero that looks like a dark image.
        assert samples["broken.jpg"].metadata["brightness"] is None
        assert samples["broken.jpg"].metadata["image_quality_version"] is None
