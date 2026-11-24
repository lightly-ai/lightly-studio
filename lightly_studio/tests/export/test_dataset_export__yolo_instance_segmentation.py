"""Tests for exporting instance segmentation to YOLO format via `DatasetExport`."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest
import yaml

from lightly_studio.core.annotation import CreatePolygon, CreateSegmentationMask
from lightly_studio.core.image.image_dataset import ImageDataset
from lightly_studio.export.image_dataset_export import ImageDatasetExport
from tests.helpers_resolvers import ImageStub, create_images


class TestDatasetExport:
    def test_to_yolo_instance_segmentation__polygon(
        self,
        tmp_path: Path,
        patch_collection: None,  # noqa: ARG002
    ) -> None:
        dataset = ImageDataset.create(name="test_dataset")
        create_images(
            db_session=dataset.session,
            collection_id=dataset.collection_id,
            images=[ImageStub(path="image0.jpg", width=100, height=50)],
        )
        samples = list(dataset)
        samples[0].add_annotation(
            annotation=CreatePolygon(class_name="dog", polygons=[[(10, 5), (50, 5), (50, 25)]])
        )

        output_folder = tmp_path / "yolo"
        ImageDatasetExport(
            session=dataset.session, dataset_id=dataset.dataset_id, samples=dataset.query()
        ).to_yolo_instance_segmentation(output_folder=output_folder)

        with open(output_folder / "data.yaml") as f:
            assert yaml.safe_load(f)["names"] == {0: "dog"}
        # Normalized by width 100 and height 50. Labelformat repeats the first vertex.
        assert (
            output_folder / "labels" / "image0.txt"
        ).read_text() == "0 0.1 0.1 0.5 0.1 0.5 0.5 0.1 0.1\n"

    def test_to_yolo_instance_segmentation__skips_masks_with_warning(
        self,
        tmp_path: Path,
        patch_collection: None,  # noqa: ARG002
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        dataset = ImageDataset.create(name="test_dataset")
        create_images(
            db_session=dataset.session,
            collection_id=dataset.collection_id,
            images=[ImageStub(path="image0.jpg", width=10, height=10)],
        )
        samples = list(dataset)
        samples[0].add_annotation(
            annotation=CreateSegmentationMask.from_rle_mask(
                class_name="dog", sample_2d=samples[0], segmentation_mask=[2, 3, 95]
            )
        )
        samples[0].add_annotation(
            annotation=CreatePolygon(class_name="dog", polygons=[[(1, 1), (5, 1), (5, 5)]])
        )

        output_folder = tmp_path / "yolo"
        with caplog.at_level(logging.WARNING):
            ImageDatasetExport(
                session=dataset.session, dataset_id=dataset.dataset_id, samples=dataset.query()
            ).to_yolo_instance_segmentation(output_folder=output_folder)

        lines = (output_folder / "labels" / "image0.txt").read_text().splitlines()
        assert len(lines) == 1
        assert "Skipped 1 segmentation mask annotations" in caplog.text

    def test_to_yolo_instance_segmentation__no_warning_without_masks(
        self,
        tmp_path: Path,
        patch_collection: None,  # noqa: ARG002
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        dataset = ImageDataset.create(name="test_dataset")
        create_images(
            db_session=dataset.session,
            collection_id=dataset.collection_id,
            images=[ImageStub(path="image0.jpg", width=10, height=10)],
        )
        samples = list(dataset)
        samples[0].add_annotation(
            annotation=CreatePolygon(class_name="dog", polygons=[[(1, 1), (5, 1), (5, 5)]])
        )

        with caplog.at_level(logging.WARNING):
            ImageDatasetExport(
                session=dataset.session, dataset_id=dataset.dataset_id, samples=dataset.query()
            ).to_yolo_instance_segmentation(output_folder=tmp_path / "yolo")

        assert "Skipped" not in caplog.text

    def test_to_yolo_instance_segmentation__multi_part_becomes_one_line(
        self,
        tmp_path: Path,
        patch_collection: None,  # noqa: ARG002
    ) -> None:
        dataset = ImageDataset.create(name="test_dataset")
        create_images(
            db_session=dataset.session,
            collection_id=dataset.collection_id,
            images=[ImageStub(path="image0.jpg", width=20, height=20)],
        )
        samples = list(dataset)
        samples[0].add_annotation(
            annotation=CreatePolygon(
                class_name="dog",
                polygons=[
                    [(1, 1), (5, 1), (5, 5)],
                    [(10, 10), (12, 10), (12, 12)],
                ],
            )
        )

        output_folder = tmp_path / "yolo"
        ImageDatasetExport(
            session=dataset.session, dataset_id=dataset.dataset_id, samples=dataset.query()
        ).to_yolo_instance_segmentation(output_folder=output_folder)

        lines = (output_folder / "labels" / "image0.txt").read_text().splitlines()
        assert len(lines) == 1

    def test_to_yolo_instance_segmentation__warns_for_one_shot_samples(
        self,
        tmp_path: Path,
        patch_collection: None,  # noqa: ARG002
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        dataset = ImageDataset.create(name="test_dataset")
        create_images(
            db_session=dataset.session,
            collection_id=dataset.collection_id,
            images=[ImageStub(path="image0.jpg", width=10, height=10)],
        )
        samples = list(dataset)
        samples[0].add_annotation(
            annotation=CreateSegmentationMask.from_rle_mask(
                class_name="dog", sample_2d=samples[0], segmentation_mask=[2, 3, 95]
            )
        )

        with caplog.at_level(logging.WARNING):
            ImageDatasetExport(
                session=dataset.session, dataset_id=dataset.dataset_id, samples=iter(samples)
            ).to_yolo_instance_segmentation(output_folder=tmp_path / "yolo")

        assert "Skipped 1 segmentation mask annotations" in caplog.text
