"""Converts annotations from Lightly Studio to Labelformat format."""

from __future__ import annotations

from argparse import ArgumentParser
from typing import Iterable
from uuid import UUID

from labelformat.model.binary_mask_segmentation import BinaryMaskSegmentation
from labelformat.model.bounding_box import BoundingBox
from labelformat.model.category import Category
from labelformat.model.image import Image
from labelformat.model.instance_segmentation import (
    ImageInstanceSegmentation,
    InstanceSegmentationInput,
    SingleInstanceSegmentation,
)
from labelformat.model.object_detection import (
    ImageObjectDetection,
    ObjectDetectionInput,
    SingleObjectDetection,
)
from sqlmodel import Session

from lightly_studio.core.image.image_sample import ImageSample
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable, AnnotationType
from lightly_studio.resolvers import annotation_label_resolver


class LightlyStudioInputBase:
    """Base class for Lightly Studio labelformat adapters."""

    def __init__(self, session: Session, dataset_id: UUID, samples: Iterable[ImageSample]) -> None:
        """Initializes the adapter.

        Args:
            session: The SQLModel session to use for database access. Used only in the
                constructor to fetch the labels for the given annotation task.
            dataset_id: The root collection ID for label retrieval.
            samples: Dataset samples.
        """
        self._samples = list(samples)
        self._label_id_to_category = _build_label_id_to_category(
            session=session, dataset_id=dataset_id
        )

    @staticmethod
    def add_cli_arguments(parser: ArgumentParser) -> None:
        """Adds CLI arguments."""
        # Add CLI arguments implementation is not needed for this class. We need it only
        # to satisfy the interface.
        raise NotImplementedError()

    def get_categories(self) -> Iterable[Category]:
        """Returns the categories for export."""
        return self._label_id_to_category.values()

    def get_images(self) -> Iterable[Image]:
        """Returns the images for export."""
        for idx, sample in enumerate(self._samples):
            yield _sample_to_image(sample=sample, image_id=idx)


class LightlyStudioObjectDetectionInput(LightlyStudioInputBase, ObjectDetectionInput):
    """Labelformat adapter for object detection backed by dataset samples and annotations."""

    def get_labels(self) -> Iterable[ImageObjectDetection]:
        """Returns the labels for export."""
        for idx, sample in enumerate(self._samples):
            yield _sample_to_image_obj_det(
                sample=sample,
                image_id=idx,
                label_id_to_category=self._label_id_to_category,
            )


class LightlyStudioInstanceSegmentationInput(LightlyStudioInputBase, InstanceSegmentationInput):
    """Labelformat adapter for instance segmentation backed by dataset samples and annotations."""

    @staticmethod
    def _sample_to_image_inst_seg(
        sample: ImageSample,
        image_id: int,
        label_id_to_category: dict[UUID, Category],
    ) -> ImageInstanceSegmentation:
        # TODO(lukas, 02/2026): We can optimise in the future to filter annotations in a DB query.
        objects = [
            _annotation_to_single_inst_seg(
                annotation=annotation,
                label_id_to_category=label_id_to_category,
                image_width=sample.width,
                image_height=sample.height,
            )
            for annotation in sample.sample_table.annotations
            if annotation.annotation_type == AnnotationType.INSTANCE_SEGMENTATION
        ]
        return ImageInstanceSegmentation(
            image=_sample_to_image(sample=sample, image_id=image_id),
            objects=objects,
        )

    def get_labels(self) -> Iterable[ImageInstanceSegmentation]:
        """Returns the labels for export."""
        for idx, sample in enumerate(self._samples):
            yield LightlyStudioInstanceSegmentationInput._sample_to_image_inst_seg(
                sample=sample,
                image_id=idx,
                label_id_to_category=self._label_id_to_category,
            )


def _build_label_id_to_category(session: Session, dataset_id: UUID) -> dict[UUID, Category]:
    labels = annotation_label_resolver.get_all_sorted_alphabetically(
        session=session,
        dataset_id=dataset_id,
    )
    # TODO(Horatiu, 09/2025): We should get only labels that are attached to Object Detection
    # annotations.
    return {
        label.annotation_label_id: Category(id=idx, name=label.annotation_label_name)
        for idx, label in enumerate(labels)
    }


def _sample_to_image(sample: ImageSample, image_id: int) -> Image:
    return Image(
        id=image_id,
        filename=sample.file_path_abs,
        width=sample.width,
        height=sample.height,
    )


def _sample_to_image_obj_det(
    sample: ImageSample,
    image_id: int,
    label_id_to_category: dict[UUID, Category],
) -> ImageObjectDetection:
    # TODO(Michal, 09/2025): We can optimise in the future to filter annotations in a DB query.
    objects = [
        _annotation_to_single_obj_det(
            annotation=annotation,
            label_id_to_category=label_id_to_category,
        )
        for annotation in sample.sample_table.annotations
        if annotation.annotation_type == AnnotationType.OBJECT_DETECTION
    ]
    return ImageObjectDetection(
        image=_sample_to_image(sample=sample, image_id=image_id),
        objects=objects,
    )


def _annotation_to_single_obj_det(
    annotation: AnnotationBaseTable, label_id_to_category: dict[UUID, Category]
) -> SingleObjectDetection:
    assert annotation.object_detection_details is not None
    box = BoundingBox(
        xmin=annotation.object_detection_details.x,
        ymin=annotation.object_detection_details.y,
        xmax=annotation.object_detection_details.x + annotation.object_detection_details.width,
        ymax=annotation.object_detection_details.y + annotation.object_detection_details.height,
    )
    category = label_id_to_category[annotation.annotation_label.annotation_label_id]
    return SingleObjectDetection(
        category=category,
        box=box,
        confidence=annotation.confidence,
    )


def _annotation_to_single_inst_seg(
    annotation: AnnotationBaseTable,
    label_id_to_category: dict[UUID, Category],
    image_width: int,
    image_height: int,
) -> SingleInstanceSegmentation:
    assert annotation.segmentation_details is not None
    assert annotation.segmentation_details.segmentation_mask is not None, (
        "Instance segmentation must have a mask."
    )
    box = BoundingBox(
        xmin=annotation.segmentation_details.x,
        ymin=annotation.segmentation_details.y,
        xmax=annotation.segmentation_details.x + annotation.segmentation_details.width,
        ymax=annotation.segmentation_details.y + annotation.segmentation_details.height,
    )
    segmentation = BinaryMaskSegmentation.from_rle(
        rle_row_wise=annotation.segmentation_details.segmentation_mask,
        width=image_width,
        height=image_height,
        bounding_box=box,
    )
    category = label_id_to_category[annotation.annotation_label.annotation_label_id]
    return SingleInstanceSegmentation(
        category=category,
        segmentation=segmentation,
    )
