"""Tests for exporting captions to COCO format via `DatasetExport`."""

from __future__ import annotations

import json
from pathlib import Path

from pytest_mock import MockerFixture

from lightly_studio.core.image.image_dataset import ImageDataset
from lightly_studio.export.image_dataset_export import ImageDatasetExport
from tests.helpers_resolvers import ImageStub, create_caption, create_images


class TestDatasetExport:
    def test_to_coco_captions(
        self,
        tmp_path: Path,
        patch_collection: None,  # noqa: ARG002
    ) -> None:
        """Tests exporting captions to COCO format."""
        dataset = ImageDataset.create(name="test_dataset")
        image = create_images(
            db_session=dataset.session,
            collection_id=dataset.collection_id,
            images=[ImageStub(path="/path/image0.jpg", width=100, height=100)],
        )[0]
        create_caption(
            session=dataset.session,
            collection_id=dataset.collection_id,
            parent_sample_id=image.sample_id,
            text="caption one",
        )

        output_json = tmp_path / "coco_annotations.json"
        ImageDatasetExport(
            session=dataset.session, dataset_id=dataset.dataset_id, samples=dataset.query()
        ).to_coco_captions(output_json=output_json)

        # Load the generated JSON and verify its content
        with open(output_json) as f:
            coco_data = json.load(f)
        assert coco_data == {
            "images": [
                {"id": 0, "file_name": "/path/image0.jpg", "width": 100, "height": 100},
            ],
            "annotations": [
                {"id": 0, "image_id": 0, "caption": "caption one"},
            ],
        }

    def test_to_coco_captions__str_path(
        self,
        tmp_path: Path,
        patch_collection: None,  # noqa: ARG002
    ) -> None:
        """Tests that a string output path is accepted for captions."""
        dataset = ImageDataset.create(name="test_dataset")

        output_json = tmp_path / "coco_annotations.json"
        ImageDatasetExport(
            session=dataset.session, dataset_id=dataset.dataset_id, samples=dataset.query()
        ).to_coco_captions(output_json=str(output_json))

        assert output_json.exists()

    def test_to_coco_captions__default_path(
        self,
        mocker: MockerFixture,
        patch_collection: None,  # noqa: ARG002
    ) -> None:
        """Tests that the default output path is used for captions when none is provided."""
        dataset = ImageDataset.create(name="test_dataset")

        # Patch Path.open so no file is created and assert the default path is used.
        mock_open = mocker.patch.object(Path, "open", autospec=True)

        ImageDatasetExport(
            session=dataset.session, dataset_id=dataset.dataset_id, samples=dataset.query()
        ).to_coco_captions()

        assert mock_open.call_args.args[0] == Path("coco_export.json")
