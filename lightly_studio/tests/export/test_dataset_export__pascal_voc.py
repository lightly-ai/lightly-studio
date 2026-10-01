"""Tests for exporting segmentation masks to Pascal VOC format via `DatasetExport`."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image as PILImage

from lightly_studio.core.annotation import CreateSegmentationMask
from lightly_studio.core.image.image_dataset import ImageDataset
from lightly_studio.export.image_dataset_export import ImageDatasetExport
from tests.helpers_resolvers import ImageStub, create_annotation_label, create_images


class TestDatasetExport:
    def test_to_pascalvoc_segmentation_mask(
        self,
        tmp_path: Path,
        patch_collection: None,  # noqa: ARG002
    ) -> None:
        """Tests exporting a single-class segmentation mask to Pascal VOC format."""
        dataset = ImageDataset.create(name="test_dataset")
        create_images(
            db_session=dataset.session,
            collection_id=dataset.collection_id,
            images=[ImageStub(path="image0.jpg", width=3, height=2)],
        )

        samples = list(dataset)
        samples[0].add_annotation(
            CreateSegmentationMask.from_rle_mask(
                class_name="dog",
                sample_2d=samples[0],
                segmentation_mask=[1, 1, 4],
            )
        )

        output_folder = tmp_path / "pascalvoc"
        ImageDatasetExport(
            session=dataset.session, dataset_id=dataset.dataset_id, samples=dataset.query()
        ).to_pascalvoc_segmentation_mask(output_folder=output_folder)

        class_map_path = output_folder / "class_id_to_name.json"
        with class_map_path.open() as f:
            class_map = json.load(f)
        assert class_map == {"0": "background", "1": "dog"}

        mask_path = output_folder / "SegmentationClass" / "image0.png"
        with PILImage.open(mask_path) as mask:
            mask_values = list(mask.getdata())
        assert mask_values == [0, 1, 0, 0, 0, 0]

    def test_to_pascalvoc_segmentation_mask__background_and_dog_labels_partial_image(
        self,
        tmp_path: Path,
        patch_collection: None,  # noqa: ARG002
    ) -> None:
        """Tests Pascal VOC export with a user-defined background class."""
        dataset = ImageDataset.create(name="test_dataset")
        create_images(
            db_session=dataset.session,
            collection_id=dataset.collection_id,
            images=[ImageStub(path="image0.jpg", width=3, height=2)],
        )
        create_annotation_label(
            session=dataset.session,
            root_collection_id=dataset.collection_id,
            label_name="background",
        )
        create_annotation_label(
            session=dataset.session,
            root_collection_id=dataset.collection_id,
            label_name="dog",
        )

        samples = list(dataset)
        samples[0].add_annotation(
            CreateSegmentationMask.from_rle_mask(
                class_name="dog",
                sample_2d=samples[0],
                segmentation_mask=[1, 1, 4],
            )
        )
        samples[0].add_annotation(
            CreateSegmentationMask.from_rle_mask(
                class_name="background",
                sample_2d=samples[0],
                segmentation_mask=[4, 1, 1],
            )
        )

        output_folder = tmp_path / "pascalvoc"
        ImageDatasetExport(
            session=dataset.session, dataset_id=dataset.dataset_id, samples=dataset.query()
        ).to_pascalvoc_segmentation_mask(output_folder=output_folder)

        class_map_path = output_folder / "class_id_to_name.json"
        with class_map_path.open() as f:
            class_map = json.load(f)
        # Two "background" classes are expected: class 0 is reserved by labelformat,
        # and class 1 is the user-defined "background" class.
        assert class_map == {"0": "background", "1": "background", "2": "dog"}

        mask_path = output_folder / "SegmentationClass" / "image0.png"
        with PILImage.open(mask_path) as mask:
            mask_values = list(mask.getdata())
        assert mask_values == [0, 2, 0, 0, 1, 0]

    def test_to_pascalvoc_segmentation_mask__two_foreground_classes_on_one_image(
        self,
        tmp_path: Path,
        patch_collection: None,  # noqa: ARG002
    ) -> None:
        """Tests Pascal VOC export with two foreground classes on one image."""
        dataset = ImageDataset.create(name="test_dataset")
        create_images(
            db_session=dataset.session,
            collection_id=dataset.collection_id,
            images=[ImageStub(path="image0.jpg", width=3, height=2)],
        )

        samples = list(dataset)
        samples[0].add_annotation(
            CreateSegmentationMask.from_rle_mask(
                class_name="cat",
                sample_2d=samples[0],
                segmentation_mask=[1, 1, 4],
            )
        )
        samples[0].add_annotation(
            CreateSegmentationMask.from_rle_mask(
                class_name="dog",
                sample_2d=samples[0],
                segmentation_mask=[4, 1, 1],
            )
        )

        output_folder = tmp_path / "pascalvoc"
        ImageDatasetExport(
            session=dataset.session, dataset_id=dataset.dataset_id, samples=dataset.query()
        ).to_pascalvoc_segmentation_mask(output_folder=output_folder)

        class_map_path = output_folder / "class_id_to_name.json"
        with class_map_path.open() as f:
            class_map = json.load(f)
        assert class_map == {"0": "background", "1": "cat", "2": "dog"}

        mask_path = output_folder / "SegmentationClass" / "image0.png"
        with PILImage.open(mask_path) as mask:
            mask_values = list(mask.getdata())

        assert mask_values == [0, 1, 0, 0, 2, 0]

    def test_to_pascalvoc_segmentation_mask__two_parts_with_same_class_on_one_image(
        self,
        tmp_path: Path,
        patch_collection: None,  # noqa: ARG002
    ) -> None:
        """Tests Pascal VOC export with two disjoint parts of the same class."""
        dataset = ImageDataset.create(name="test_dataset")
        create_images(
            db_session=dataset.session,
            collection_id=dataset.collection_id,
            images=[ImageStub(path="image0.jpg", width=3, height=2)],
        )

        samples = list(dataset)
        samples[0].add_annotation(
            CreateSegmentationMask.from_rle_mask(
                class_name="dog",
                sample_2d=samples[0],
                segmentation_mask=[1, 1, 4],
            )
        )
        samples[0].add_annotation(
            CreateSegmentationMask.from_rle_mask(
                class_name="dog",
                sample_2d=samples[0],
                segmentation_mask=[4, 1, 1],
            )
        )

        output_folder = tmp_path / "pascalvoc"
        ImageDatasetExport(
            session=dataset.session, dataset_id=dataset.dataset_id, samples=dataset.query()
        ).to_pascalvoc_segmentation_mask(output_folder=output_folder)

        class_map_path = output_folder / "class_id_to_name.json"
        with class_map_path.open() as f:
            class_map = json.load(f)
        assert class_map == {"0": "background", "1": "dog"}

        mask_path = output_folder / "SegmentationClass" / "image0.png"
        with PILImage.open(mask_path) as mask:
            mask_values = list(mask.getdata())
        assert mask_values == [0, 1, 0, 0, 1, 0]

    def test_to_pascalvoc_segmentation_mask__two_images_with_parts_of_same_class(
        self,
        tmp_path: Path,
        patch_collection: None,  # noqa: ARG002
    ) -> None:
        """Tests Pascal VOC export with the same class spread across two images."""
        dataset = ImageDataset.create(name="test_dataset")
        create_images(
            db_session=dataset.session,
            collection_id=dataset.collection_id,
            images=[
                ImageStub(path="image0.jpg", width=3, height=2),
                ImageStub(path="image1.jpg", width=3, height=2),
            ],
        )

        samples = list(dataset)
        sample_by_name = {sample.file_name: sample for sample in samples}

        sample_by_name["image0.jpg"].add_annotation(
            CreateSegmentationMask.from_rle_mask(
                class_name="dog",
                sample_2d=sample_by_name["image0.jpg"],
                segmentation_mask=[1, 1, 4],
            )
        )
        sample_by_name["image1.jpg"].add_annotation(
            CreateSegmentationMask.from_rle_mask(
                class_name="dog",
                sample_2d=sample_by_name["image1.jpg"],
                segmentation_mask=[4, 1, 1],
            )
        )

        output_folder = tmp_path / "pascalvoc"
        ImageDatasetExport(
            session=dataset.session, dataset_id=dataset.dataset_id, samples=dataset.query()
        ).to_pascalvoc_segmentation_mask(output_folder=output_folder)

        class_map_path = output_folder / "class_id_to_name.json"
        with class_map_path.open() as f:
            class_map = json.load(f)
        assert class_map == {"0": "background", "1": "dog"}

        mask_path_0 = output_folder / "SegmentationClass" / "image0.png"
        with PILImage.open(mask_path_0) as mask_0:
            mask_values_0 = list(mask_0.getdata())
        assert mask_values_0 == [0, 1, 0, 0, 0, 0]

        mask_path_1 = output_folder / "SegmentationClass" / "image1.png"
        with PILImage.open(mask_path_1) as mask_1:
            mask_values_1 = list(mask_1.getdata())
        assert mask_values_1 == [0, 0, 0, 0, 1, 0]
