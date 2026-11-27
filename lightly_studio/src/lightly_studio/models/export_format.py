"""Export format models."""

from enum import Enum


class ExportFormat(str, Enum):
    """Export formats of the export endpoints and the export transport."""

    CAPTION_COCO = "caption_coco"
    CLASSIFICATION_CSV = "classification_csv"
    OBJECT_DETECTION_COCO = "object_detection_coco"
    OBJECT_DETECTION_YOLO = "object_detection_yolo"
    # COCO instance segmentation with polygons and masks. The name stays for API compatibility.
    SEGMENTATION_MASK_COCO = "segmentation_mask_coco"
    INSTANCE_SEGMENTATION_YOLO = "instance_segmentation_yolo"
    PASCAL_VOC = "pascal_voc"
    YOUTUBE_VIS_SEGMENTATION = "youtube_vis_segmentation"
