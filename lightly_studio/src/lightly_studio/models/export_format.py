"""Export format models."""

from enum import Enum


class ExportFormat(str, Enum):
    """Supported export formats for API export endpoints."""

    OBJECT_DETECTION_COCO = "object_detection_coco"
    SEGMENTATION_MASK_COCO = "segmentation_mask_coco"
    PASCAL_VOC = "pascal_voc"
    YOUTUBE_VIS_SEGMENTATION = "youtube_vis_segmentation"
