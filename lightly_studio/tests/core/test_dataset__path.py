from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from lightly_studio import Dataset


class TestDataset:
    def test_dataset_add_samples_from_path__valid(
        self,
        patch_dataset: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        images_path = tmp_path / "my_dataset"
        images_path.mkdir()
        _create_sample_images(
            [
                images_path / "image1.jpg",
                images_path / "image2.png",
                images_path / "image3.BMP",
                images_path / "subfolder" / "image4.jpg",
            ]
        )

        dataset = Dataset.create(name="test_dataset")
        dataset.add_samples_from_path(path=images_path)

        samples = dataset.query().to_list()
        assert len(samples) == 4
        assert {s.file_name for s in samples} == {
            "image1.jpg",
            "image2.png",
            "image3.BMP",
            "image4.jpg",
        }
        # Check that embeddings were created
        assert all(len(sample.inner.sample.embeddings) == 1 for sample in samples)

    def test_dataset_add_samples_from_path__file_path(
        self,
        patch_dataset: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        images_path = tmp_path / "file.txt"
        images_path.touch()

        dataset = Dataset.create(name="test_dataset")
        with pytest.raises(ValueError, match="File is not an image:.*file.txt"):
            dataset.add_samples_from_path(path=images_path)

    def test_dataset_add_samples_from_path__non_existent_dir(
        self,
        patch_dataset: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        images_path = tmp_path / "non_existent"

        dataset = Dataset.create(name="test_dataset")
        with pytest.raises(ValueError, match="Path does not exist:.*non_existent"):
            dataset.add_samples_from_path(path=images_path)

    def test_dataset_add_samples_from_path__empty_dir(
        self,
        patch_dataset: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        images_path = tmp_path / "empty"
        images_path.mkdir()

        dataset = Dataset.create(name="test_dataset")
        dataset.add_samples_from_path(path=images_path)
        assert len(dataset._inner.get_samples()) == 0

    def test_dataset_add_samples_from_path__corrupt_file(
        self,
        patch_dataset: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        images_path = tmp_path / "corrupt"
        images_path.mkdir()
        image_path = images_path / "im1.jpg"
        image_path.write_text("corrupt data")

        dataset = Dataset.create(name="test_dataset")
        dataset.add_samples_from_path(path=images_path)
        assert len(dataset._inner.get_samples()) == 0

    def test_dataset_add_samples_from_path__recursion(
        self,
        patch_dataset: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        images_path = tmp_path / "my_dataset"
        images_path.mkdir()
        _create_sample_images(
            [
                images_path / "image1.jpg",
                images_path / "image2.png",
                images_path / "image3.BMP",
                images_path / "subfolder" / "im4.jpg",
            ]
        )

        dataset = Dataset.create(name="test_dataset")
        dataset.add_samples_from_path(path=images_path / "*.*")
        assert len(dataset._inner.get_samples()) == 3

    def test_dataset_add_samples_from_path__allowed_extensions(
        self,
        patch_dataset: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        images_path = tmp_path / "my_dataset"
        images_path.mkdir()
        _create_sample_images(
            [
                images_path / "image1.jpg",
                images_path / "image2.png",
                images_path / "image3.BMP",
                images_path / "subfolder" / "im4.jpg",
            ]
        )

        dataset = Dataset.create(name="test_dataset")
        dataset.add_samples_from_path(path=images_path / "**" / "*.jpg")
        assert len(dataset._inner.get_samples()) == 2

        dataset_allowed_extensions = Dataset.create(name="test_dataset_allowed_extensions")
        dataset_allowed_extensions.add_samples_from_path(
            path=images_path / "**", allowed_extensions=[".png", ".bmp"]
        )
        assert len(dataset_allowed_extensions._inner.get_samples()) == 2

    def test_dataset_add_samples_from_path__duplication(
        self,
        patch_dataset: None,  # noqa: ARG002
        capsys: pytest.CaptureFixture[str],
        tmp_path: Path,
    ) -> None:
        images_path = tmp_path / "my_dataset"
        images_path.mkdir()
        _create_sample_images(
            [
                images_path / "image1.jpg",
                images_path / "image2.png",
                images_path / "image3.BMP",
                images_path / "subfolder" / "im4.jpg",
            ]
        )

        dataset = Dataset.create(name="test_dataset")
        dataset.add_samples_from_path(path=images_path)

        _create_sample_images(
            [
                images_path / "image5.png",
                images_path / "image6.BMP",
            ]
        )

        # Only two are new, the other four are already in the dataset
        dataset.add_samples_from_path(path=images_path)
        assert len(dataset._inner.get_samples()) == 6

        captured = capsys.readouterr()
        assert "Added 2 out of 6 new samples to the dataset." in captured.out
        assert f"Examples of paths that were not added:  {images_path}" in captured.out

    def test_dataset_add_samples_from_path__dont_embed(
        self,
        patch_dataset: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        _create_sample_images([tmp_path / "image1.jpg"])

        dataset = Dataset.create(name="test_dataset")
        dataset.add_samples_from_path(path=tmp_path, embed=False)

        samples = dataset.query().to_list()
        assert len(samples) == 1
        assert len(samples[0].inner.sample.embeddings) == 0

    def test_dataset_add_samples_from_path__tag_by_folder_depth_1(
        self,
        patch_dataset: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        images_path = tmp_path / "data"
        images_path.mkdir()
        _create_sample_images(
            [
                images_path / "class1" / "image1.jpg",
                images_path / "class1" / "image2.jpg",
                images_path / "class2" / "image3.jpg",
                images_path / "class2" / "subtype" / "image4.jpg",
            ]
        )

        dataset = Dataset.create(name="test_dataset")
        dataset.add_samples_from_path(path=images_path, tag_depth=1)

        samples = dataset.query().to_list()
        assert len(samples) == 4

        samples_by_name = {s.file_name: s for s in samples}
        assert samples_by_name["image1.jpg"].tags == {"class1"}
        assert samples_by_name["image2.jpg"].tags == {"class1"}
        assert samples_by_name["image3.jpg"].tags == {"class2"}
        assert samples_by_name["image4.jpg"].tags == {"class2"}

    def test_dataset_add_samples_from_path__tag_by_folder_depth_2(
        self,
        patch_dataset: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        images_path = tmp_path / "data"
        images_path.mkdir()
        _create_sample_images(
            [
                images_path / "class1" / "image1.jpg",
                images_path / "class1" / "subtype_a" / "image2.jpg",
                images_path / "class2" / "subtype_b" / "image3.jpg",
                images_path / "class2" / "subtype_c" / "variant" / "image4.jpg",
            ]
        )

        dataset = Dataset.create(name="test_dataset")
        dataset.add_samples_from_path(path=images_path, tag_depth=2)

        samples = dataset.query().to_list()
        assert len(samples) == 4

        samples_by_name = {s.file_name: s for s in samples}
        assert samples_by_name["image1.jpg"].tags == {"class1"}
        assert samples_by_name["image2.jpg"].tags == {"class1", "subtype_a"}
        assert samples_by_name["image3.jpg"].tags == {"class2", "subtype_b"}
        assert samples_by_name["image4.jpg"].tags == {"class2", "subtype_c"}

    def test_dataset_add_samples_from_path__tag_by_folder_depth_disabled(
        self,
        patch_dataset: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        images_path = tmp_path / "data"
        images_path.mkdir()
        _create_sample_images(
            [
                images_path / "class1" / "image1.jpg",
                images_path / "class2" / "image2.jpg",
            ]
        )

        dataset = Dataset.create(name="test_dataset")
        dataset.add_samples_from_path(path=images_path, tag_depth=0)

        samples = dataset.query().to_list()
        assert len(samples) == 2
        assert all(len(s.tags) == 0 for s in samples)


def _create_sample_images(image_paths: list[Path]) -> None:
    for image_path in image_paths:
        image_path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (10, 10)).save(image_path)
