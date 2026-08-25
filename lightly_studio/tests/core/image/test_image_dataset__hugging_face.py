from pathlib import Path

import pytest
from PIL import Image

from lightly_studio import ImageDataset


class TestDataset:
    def test_add_images_from_hugging_face(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        image = Image.new("RGB", (12, 8))
        hugging_face_dataset = [{"image": image}]

        dataset = ImageDataset.create(name="test_dataset")
        dataset.add_images_from_hugging_face(
            hugging_face_dataset=hugging_face_dataset,
            images_path=tmp_path / "images",
            embed=False,
        )

        sample = dataset.query().to_list()[0]
        assert sample.file_name.startswith("00000000_")
        assert sample.file_name.endswith("_image.png")
        assert sample.width == 12
        assert sample.height == 8
        assert Path(sample.file_path_abs).is_file()

    def test_add_images_from_hugging_face__custom_column_and_limit(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        hugging_face_dataset = [
            {"photo": Image.new("RGB", (10, 10))},
            {"photo": Image.new("RGB", (20, 20))},
        ]

        dataset = ImageDataset.create(name="test_dataset")
        dataset.add_images_from_hugging_face(
            hugging_face_dataset=hugging_face_dataset,
            images_path=tmp_path / "images",
            image_column="photo",
            embed=False,
            limit=1,
        )

        samples = dataset.query().to_list()
        assert len(samples) == 1
        assert samples[0].width == 10

    def test_add_images_from_hugging_face__missing_column(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        dataset = ImageDataset.create(name="test_dataset")

        with pytest.raises(ValueError, match="has no 'image' column"):
            dataset.add_images_from_hugging_face(
                hugging_face_dataset=[{"photo": Image.new("RGB", (10, 10))}],
                images_path=tmp_path / "images",
                embed=False,
            )

    def test_add_images_from_hugging_face__invalid_image(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        dataset = ImageDataset.create(name="test_dataset")

        with pytest.raises(ValueError, match="must contain a Pillow image"):
            dataset.add_images_from_hugging_face(
                hugging_face_dataset=[{"image": "image.jpg"}],
                images_path=tmp_path / "images",
                embed=False,
            )
