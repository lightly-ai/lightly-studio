from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image

from lightly_studio import Dataset


class TestDataset:
    def test_add_samples_from_coco_caption__details_valid(
        self,
        patch_dataset: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        # Create and save the coco json file containing the captions
        annotations_path = tmp_path / "annotations.json"
        _get_captions_input(annotations_path=annotations_path)

        # Create images
        images_path = _create_valid_samples(tmp_path)

        # Run the test
        dataset = Dataset.create(name="test_dataset")
        dataset.add_samples_from_coco_caption(
            annotations_json=annotations_path,
            images_path=images_path,
        )
        assert dataset.name == "test_dataset"
        samples = list(dataset)

        assert len(samples) == 2
        assert {s.file_name for s in samples} == {"image1.jpg", "image2.jpg"}
        assert all(
            len(s.inner.sample.embeddings) == 1 for s in samples
        )  # Embeddings should be generated

        # Assert captions
        captions_map = {
            s.file_name: sorted(c.text for c in s.inner.sample.captions) for s in samples
        }

        assert captions_map == {
            "image1.jpg": ["Caption 1 of image 1", "Caption 2 of image 1"],
            "image2.jpg": ["Caption 1 of image 2"],
        }

    def test_add_samples_from_coco_caption__corrupted_json(
        self,
        patch_dataset: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        annotations_path = tmp_path / "annotations.json"
        annotations_path.write_text("{ this is not valid json }")
        images_path = _create_valid_samples(tmp_path)

        dataset = Dataset.create(name="test_dataset")
        with pytest.raises(json.JSONDecodeError):
            dataset.add_samples_from_coco_caption(
                annotations_json=annotations_path,
                images_path=images_path,
            )

    def test_add_samples_from_coco_caption__annotations_json_no_file(
        self,
        patch_dataset: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        annotations_path = tmp_path / "annotations.json"
        images_path = tmp_path / "images"

        dataset = Dataset.create(name="test_dataset")
        with pytest.raises(
            FileNotFoundError, match=f"COCO caption json file not found: '{annotations_path}'"
        ):
            dataset.add_samples_from_coco_caption(
                annotations_json=annotations_path,
                images_path=images_path,
            )

    def test_add_samples_from_coco_caption__annotations_json_wrong_suffix(
        self,
        patch_dataset: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        annotations_path = tmp_path / "annotations.invalid_suffix"
        _get_captions_input(annotations_path=annotations_path)

        images_path = tmp_path / "images"

        dataset = Dataset.create(name="test_dataset")
        with pytest.raises(
            FileNotFoundError, match=f"COCO caption json file not found: '{annotations_path}'"
        ):
            dataset.add_samples_from_coco_caption(
                annotations_json=annotations_path,
                images_path=images_path,
            )

    def test_add_samples_from_coco_caption__dont_embed(
        self,
        patch_dataset: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        annotations_path = tmp_path / "annotations.json"
        _get_captions_input(annotations_path=annotations_path)
        images_path = _create_valid_samples(tmp_path)

        # Run the test
        dataset = Dataset.create(name="test_dataset")
        dataset.add_samples_from_coco_caption(
            annotations_json=annotations_path,
            images_path=images_path,
            embed=False,
        )

        # Check that an embedding was not created
        samples = list(dataset)
        assert all(len(sample.inner.sample.embeddings) == 0 for sample in samples)


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


def _get_captions_input(annotations_path: Path) -> None:
    """Creates a coco caption json and saves it for testing.

    Args:
        annotations_path: The path of the annotation json file.
    """
    coco_caption_dict = {
        "images": [
            {"id": 1, "file_name": "image1.jpg", "width": 640, "height": 480},
            {"id": 2, "file_name": "image2.jpg", "width": 640, "height": 480},
        ],
        "annotations": [
            {
                "id": 1,
                "image_id": 1,
                "caption": "Caption 1 of image 1",
            },
            {
                "id": 2,
                "image_id": 1,
                "caption": "Caption 2 of image 1",
            },
            {
                "id": 3,
                "image_id": 2,
                "caption": "Caption 1 of image 2",
            },
        ],
    }
    annotations_path.write_text(json.dumps(coco_caption_dict))
