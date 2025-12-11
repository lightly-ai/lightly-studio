"""Helper module for exporting datasets in COCO captions format."""

from __future__ import annotations

from typing import Iterable, TypedDict

from lightly_studio.core.image_sample import ImageSample


class CocoCaptionImage(TypedDict):
    """Image schema for COCO captions format."""

    id: int
    file_name: str
    width: int
    height: int


class CocoCaptionAnnotation(TypedDict):
    """Annotation schema for COCO captions format."""

    id: int
    image_id: int
    caption: str


class CocoCaptionsJson(TypedDict):
    """COCO captions JSON schema."""

    images: list[CocoCaptionImage]
    annotations: list[CocoCaptionAnnotation]


def to_coco_captions_dict(samples: Iterable[ImageSample]) -> CocoCaptionsJson:
    """Convert samples with captions to a COCO captions dictionary.

    Args:
        samples: The samples to export.

    Returns:
        A dictionary in COCO captions format.
    """
    coco_images: list[CocoCaptionImage] = []
    coco_annotations: list[CocoCaptionAnnotation] = []
    annotation_id = 0

    for image_id, image in enumerate(samples):
        coco_images.append(
            {
                "id": image_id,
                "file_name": image.file_path_abs,
                "width": image.width,
                "height": image.height,
            }
        )
        for caption in image.captions:
            coco_annotations.append(
                {
                    "id": annotation_id,
                    "image_id": image_id,
                    "caption": caption,
                }
            )
            annotation_id += 1

    return {
        "images": coco_images,
        "annotations": coco_annotations,
    }
