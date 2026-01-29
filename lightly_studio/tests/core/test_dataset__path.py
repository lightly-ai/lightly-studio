from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image
from pytest_mock import MockerFixture as Mocker
from sqlmodel import Session

from lightly_studio import ImageDataset
from lightly_studio.core import add_images
from tests import helpers_resolvers


class TestDataset:
    def test_dataset_add_images_from_path__valid(
        self,
        patch_collection: None,  # noqa: ARG002
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

        dataset = ImageDataset.create(name="test_dataset")
        dataset.add_images_from_path(path=images_path)

        samples = dataset.query().to_list()
        assert len(samples) == 4
        assert {s.file_name for s in samples} == {
            "image1.jpg",
            "image2.png",
            "image3.BMP",
            "image4.jpg",
        }
        # Check that embeddings were created
        assert all(len(sample.sample_table.embeddings) == 1 for sample in samples)

    def test_dataset_add_images_from_path__file_path(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        images_path = tmp_path / "file.txt"
        images_path.touch()

        dataset = ImageDataset.create(name="test_dataset")
        with pytest.raises(ValueError, match="File is not an image:.*file.txt"):
            dataset.add_images_from_path(path=images_path)

    def test_dataset_add_images_from_path__non_existent_dir(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        images_path = tmp_path / "non_existent"

        dataset = ImageDataset.create(name="test_dataset")
        with pytest.raises(ValueError, match="Path does not exist:.*non_existent"):
            dataset.add_images_from_path(path=images_path)

    def test_dataset_add_images_from_path__empty_dir(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        images_path = tmp_path / "empty"
        images_path.mkdir()

        dataset = ImageDataset.create(name="test_dataset")
        dataset.add_images_from_path(path=images_path)
        assert len(list(dataset)) == 0

    def test_dataset_add_images_from_path__corrupt_file(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        images_path = tmp_path / "corrupt"
        images_path.mkdir()
        image_path = images_path / "im1.jpg"
        image_path.write_text("corrupt data")

        dataset = ImageDataset.create(name="test_dataset")
        dataset.add_images_from_path(path=images_path)
        assert len(list(dataset)) == 0

    def test_dataset_add_images_from_path__recursion(
        self,
        patch_collection: None,  # noqa: ARG002
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

        dataset = ImageDataset.create(name="test_dataset")
        dataset.add_images_from_path(path=images_path / "*.*")
        assert len(list(dataset)) == 3

    def test_dataset_add_images_from_path__allowed_extensions(
        self,
        patch_collection: None,  # noqa: ARG002
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

        dataset = ImageDataset.create(name="test_dataset")
        dataset.add_images_from_path(path=images_path / "**" / "*.jpg")
        assert len(list(dataset)) == 2

        dataset_allowed_extensions = ImageDataset.create(name="test_dataset_allowed_extensions")
        dataset_allowed_extensions.add_images_from_path(
            path=images_path / "**", allowed_extensions=[".png", ".bmp"]
        )
        assert len(list(dataset_allowed_extensions)) == 2

    def test_dataset_add_images_from_path__duplication(
        self,
        patch_collection: None,  # noqa: ARG002
        caplog: pytest.LogCaptureFixture,
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

        import logging

        caplog.set_level(logging.INFO)

        dataset = ImageDataset.create(name="test_dataset")
        dataset.add_images_from_path(path=images_path)

        _create_sample_images(
            [
                images_path / "image5.png",
                images_path / "image6.BMP",
            ]
        )

        # Only two are new, the other four are already in the dataset
        dataset.add_images_from_path(path=images_path)
        assert len(list(dataset)) == 6

        log_text = caplog.text
        assert "Added 2 out of 6 new samples to the dataset." in log_text
        assert "Examples of paths that were not added:" in log_text
        assert f"{images_path}" in log_text

    def test_dataset_add_images_from_path__dont_embed(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        _create_sample_images([tmp_path / "image1.jpg"])

        dataset = ImageDataset.create(name="test_dataset")
        dataset.add_images_from_path(path=tmp_path, embed=False)

        # Check that embeddings were not created
        samples = dataset.query().to_list()
        assert len(samples) == 1
        assert len(samples[0].sample_table.embeddings) == 0

    def test_add_images_from_path_calls_tag_samples_by_directory(
        self,
        patch_collection: None,  # noqa: ARG002
        db_session: Session,
        tmp_path: Path,
        mocker: Mocker,
    ) -> None:
        """Tests that ImageDataset.add_images_from_path correctly calls the helper."""
        spy_tagger = mocker.spy(add_images, "tag_samples_by_directory")

        _create_sample_images([tmp_path / "image1.jpg"])
        dataset_table = helpers_resolvers.create_collection(db_session, "test_dataset")
        dataset = ImageDataset(collection=dataset_table)
        dataset.session = db_session

        dataset.add_images_from_path(path=str(tmp_path), tag_depth=0, embed=False)

        spy_tagger.assert_called_once_with(
            session=db_session,
            collection_id=dataset.dataset_id,
            input_path=str(tmp_path),
            sample_ids=mocker.ANY,
            tag_depth=0,
        )


def _create_sample_images(image_paths: list[Path]) -> None:
    for image_path in image_paths:
        image_path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (10, 10)).save(image_path)
