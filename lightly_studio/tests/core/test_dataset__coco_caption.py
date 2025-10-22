from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image

from lightly_studio import Dataset
from lightly_studio.models.image import ImageTable
from lightly_studio.resolvers import caption_resolver


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
        samples = dataset._inner.get_samples()
        samples = sorted(samples, key=lambda sample: sample.file_path_abs)

        assert len(samples) == 2
        assert {s.file_name for s in samples} == {"image1.jpg", "image2.jpg"}
        assert all(len(s.embeddings) == 1 for s in samples)  # Embeddings should be generated

        # Assert captions
        captions_result = caption_resolver.get_all(
            session=dataset.session, dataset_id=dataset.dataset_id
        )
        assert len(captions_result.captions) == 3
        assert captions_result.total_count == 3
        assert captions_result.next_cursor is None
        # Collect all the filename x caption pairs and assert they are as expected
        assert {
            (c.sample.file_name, c.text)
            for c in captions_result.captions
            if isinstance(c.sample, ImageTable)
        } == {
            ("image1.jpg", "Caption 1 of image 1"),
            ("image1.jpg", "Caption 2 of image 1"),
            ("image2.jpg", "Caption 1 of image 2"),
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
        samples = dataset._inner.get_samples()
        assert all(len(sample.embeddings) == 0 for sample in samples)


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
