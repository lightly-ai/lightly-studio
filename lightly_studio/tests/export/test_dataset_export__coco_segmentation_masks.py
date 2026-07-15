"""Tests for exporting segmentation masks to COCO format via `DatasetExport`."""

from __future__ import annotations

import json
from pathlib import Path

from lightly_studio.core.annotation import CreateSegmentationMask
from lightly_studio.core.image.image_dataset import ImageDataset
from lightly_studio.export.image_dataset_export import ImageDatasetExport
from lightly_studio.models.annotation.annotation_base import (
    AnnotationCreate,
    AnnotationType,
)
from lightly_studio.resolvers import annotation_resolver
from tests.helpers_resolvers import ImageStub, create_annotation_label, create_images


class TestDatasetExport:
    def test_to_coco_segmentation_masks(
        self,
        tmp_path: Path,
        patch_collection: None,  # noqa: ARG002
    ) -> None:
        """Tests exporting segmentation masks to COCO format."""
        dataset = ImageDataset.create(name="test_dataset")
        create_images(
            db_session=dataset.session,
            collection_id=dataset.collection_id,
            images=[ImageStub(path="image0.jpg", width=10, height=10)],
        )

        samples = list(dataset)
        samples[0].add_annotation(
            CreateSegmentationMask.from_rle_mask(
                class_name="dog",
                sample_2d=samples[0],
                segmentation_mask=[2, 3, 7, 2, 86],
            )
        )

        output_json = tmp_path / "task_inst_seg_1.json"
        ImageDatasetExport(
            session=dataset.session, dataset_id=dataset.dataset_id, samples=dataset.query()
        ).to_coco_segmentation_masks(output_json=output_json)

        # Load the generated JSON and verify its content
        with open(output_json) as f:
            coco_data = json.load(f)
        assert coco_data == {
            "images": [
                {"id": 0, "file_name": "image0.jpg", "width": 10, "height": 10},
            ],
            "categories": [{"id": 0, "name": "dog"}],
            "annotations": [
                {
                    "image_id": 0,
                    "category_id": 0,
                    "segmentation": {"counts": [20, 2, 8, 2, 8, 1, 59], "size": [10, 10]},
                    "bbox": [2.0, 0.0, 3.0, 2.0],
                    "iscrowd": 1,
                },
            ],
        }

    def test_to_coco_segmentation_masks__skips_missing_mask(
        self,
        tmp_path: Path,
        patch_collection: None,  # noqa: ARG002
    ) -> None:
        """Tests that annotations without a mask are skipped."""
        dataset = ImageDataset.create(name="test_dataset")
        images = create_images(
            db_session=dataset.session,
            collection_id=dataset.collection_id,
            images=[ImageStub(path="image0.jpg", width=10, height=10)],
        )

        label = create_annotation_label(
            session=dataset.session, root_collection_id=dataset.collection_id, label_name="dog"
        )
        # Create an annotation without a mask
        annotation_resolver.create_many(
            session=dataset.session,
            parent_collection_id=dataset.collection_id,
            annotations=[
                AnnotationCreate(
                    parent_sample_id=images[0].sample_id,
                    annotation_label_id=label.annotation_label_id,
                    annotation_type=AnnotationType.SEGMENTATION_MASK,
                    x=2,
                    y=0,
                    width=3,
                    height=2,
                    segmentation_mask=None,
                ),
            ],
        )

        output_json = tmp_path / "task_inst_seg_skip.json"
        ImageDatasetExport(
            session=dataset.session, dataset_id=dataset.dataset_id, samples=dataset.query()
        ).to_coco_segmentation_masks(output_json=output_json)

        # Load the generated JSON and verify its content
        with open(output_json) as f:
            coco_data = json.load(f)
        # Annotation should be skipped, categories and images should still be there
        assert coco_data == {
            "images": [
                {"id": 0, "file_name": "image0.jpg", "width": 10, "height": 10},
            ],
            "categories": [{"id": 0, "name": "dog"}],
            "annotations": [],
        }
