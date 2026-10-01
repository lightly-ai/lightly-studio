"""Converts annotations from Lightly Studio to Labelformat format.

The adapters here are sample-type-agnostic: they iterate over `Sample` objects and their
annotations and delegate the sample-to-image mapping (filename and dimensions) to a
`sample_to_image` strategy. This lets image samples and video frame samples share the same
export logic while differing only in how a sample maps to a labelformat `Image`.
"""

from __future__ import annotations

from argparse import ArgumentParser
from collections.abc import Iterable
from typing import Protocol
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

from lightly_studio.core.sample import Sample
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable, AnnotationType
from lightly_studio.resolvers import annotation_label_resolver


class SampleToImage(Protocol):
    """Strategy mapping a sample to a labelformat `Image` (its file name and dimensions)."""

    def __call__(self, sample: Sample, image_id: int, use_relative_filename: bool) -> Image:
        """Returns the labelformat `Image` for `sample`.

        Args:
            sample: The sample to map.
            image_id: The id to assign to the returned image.
            use_relative_filename: Whether to use a relative file name (YOLO, Pascal VOC)
                rather than the absolute path (COCO).
        """
        ...


class LightlyStudioInputBase:
    """Base class for Lightly Studio labelformat adapters."""

    CATEGORY_ID_START = 0
    # Whether images are referenced by a relative file name. COCO stores the (absolute) path
    # verbatim, while YOLO and Pascal VOC join the file name with the output directory, so
    # those must use a relative name.
    USE_RELATIVE_FILENAME = False

    def __init__(
        self,
        session: Session,
        dataset_id: UUID,
        samples: Iterable[Sample],
        annotation_collection_id: UUID | None,
        sample_to_image: SampleToImage,
    ) -> None:
        """Initializes the adapter.

        Args:
            session: The SQLModel session to use for database access. Used only in the
                constructor to fetch the labels for the given dataset.
            dataset_id: The dataset ID for label retrieval.
            samples: Dataset samples.
            annotation_collection_id: If provided, only annotations belonging to this
                annotation collection are exported. If None, all annotations are exported.
            sample_to_image: Strategy mapping a sample to a labelformat `Image`.
        """
        self._samples = list(samples)
        self._annotation_collection_id = annotation_collection_id
        self._sample_to_image = sample_to_image
        self._label_id_to_category = _build_label_id_to_category(
            session=session,
            dataset_id=dataset_id,
            category_id_start=self.CATEGORY_ID_START,
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
            yield self._sample_to_image(
                sample=sample, image_id=idx, use_relative_filename=self.USE_RELATIVE_FILENAME
            )

    def _annotations_of_collection_and_type(
        self, sample: Sample, annotation_type: AnnotationType
    ) -> Iterable[AnnotationBaseTable]:
        # TODO(malte, 07/2026): We can optimise in the future to filter annotations in a DB
        # query instead of loading every annotation per sample and filtering in Python.
        for annotation in sample.sample_table.annotations:
            if annotation.annotation_type != annotation_type:
                continue
            if (
                self._annotation_collection_id is None
                or annotation.annotation_collection_id == self._annotation_collection_id
            ):
                yield annotation


class LightlyStudioObjectDetectionInput(LightlyStudioInputBase, ObjectDetectionInput):
    """Labelformat adapter for object detection backed by dataset samples and annotations."""

    def get_labels(self) -> Iterable[ImageObjectDetection]:
        """Returns the labels for export."""
        for idx, sample in enumerate(self._samples):
            objects = [
                _annotation_to_single_obj_det(
                    annotation=annotation,
                    label_id_to_category=self._label_id_to_category,
                )
                for annotation in self._annotations_of_collection_and_type(
                    sample=sample, annotation_type=AnnotationType.OBJECT_DETECTION
                )
            ]
            yield ImageObjectDetection(
                image=self._sample_to_image(
                    sample=sample, image_id=idx, use_relative_filename=self.USE_RELATIVE_FILENAME
                ),
                objects=objects,
            )


class LightlyStudioYOLOObjectDetectionInput(LightlyStudioObjectDetectionInput):
    """Labelformat adapter for YOLO object detection export.

    Uses relative filenames so the YOLO writer places label files inside the output
    ``labels`` directory. The base adapter uses absolute paths, which are fine for COCO
    (stored verbatim as strings) but would break YOLO: the writer joins the filename
    with the output directory to build each label file path, and an absolute path would
    escape that directory.
    """

    USE_RELATIVE_FILENAME = True


class LightlyStudioInstanceSegmentationInput(LightlyStudioInputBase, InstanceSegmentationInput):
    """Labelformat adapter for segmentation mask backed by dataset samples and annotations."""

    def get_labels(self) -> Iterable[ImageInstanceSegmentation]:
        """Returns the labels for export."""
        for idx, sample in enumerate(self._samples):
            image = self._sample_to_image(
                sample=sample, image_id=idx, use_relative_filename=self.USE_RELATIVE_FILENAME
            )
            objects = []
            for annotation in self._annotations_of_collection_and_type(
                sample=sample, annotation_type=AnnotationType.SEGMENTATION_MASK
            ):
                obj = _annotation_to_single_inst_seg(
                    annotation=annotation,
                    label_id_to_category=self._label_id_to_category,
                    image_width=image.width,
                    image_height=image.height,
                )
                # TODO(lukas, 03/2026): workaround needed because
                # annotation.segmentation_details.segmentation_mask can be None.
                # See lightly_studio/src/lightly_studio/models/annotation/segmentation.py.
                if obj is not None:
                    objects.append(obj)
            yield ImageInstanceSegmentation(image=image, objects=objects)


class LightlyStudioPascalVOCInstanceSegmentationInput(LightlyStudioInstanceSegmentationInput):
    """Labelformat adapter for Pascal VOC export from segmentation mask annotations."""

    # TODO(Leonardo, 03/2026): Ensure Pascal VOC export maps user-defined background to class ID 0
    # and void/ignore to 255 for spec compliance.
    CATEGORY_ID_START = 1
    # Pascal VOC derives mask filenames from image names, so an absolute path cannot be used.
    USE_RELATIVE_FILENAME = True


def _build_label_id_to_category(
    session: Session,
    dataset_id: UUID,
    category_id_start: int = 0,
) -> dict[UUID, Category]:
    labels = annotation_label_resolver.get_all_sorted_alphabetically(
        session=session,
        dataset_id=dataset_id,
    )
    # TODO(Horatiu, 09/2025): We should get only labels that are attached to Object Detection
    # annotations.
    return {
        label.annotation_label_id: Category(
            id=category_id_start + idx,
            name=label.annotation_label_name,
        )
        for idx, label in enumerate(labels)
    }


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
) -> SingleInstanceSegmentation | None:
    if annotation.segmentation_details is None:
        return None
    if annotation.segmentation_details.segmentation_mask is None:
        return None

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
