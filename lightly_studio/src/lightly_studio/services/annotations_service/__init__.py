"""Services for annotations operations."""

from lightly_studio.services.annotations_service.create_annotation import (
    create_annotation,
)
from lightly_studio.services.annotations_service.delete_annotation import (
    delete_annotation,
)
from lightly_studio.services.annotations_service.get_annotation_by_id import (
    get_annotation_by_id,
)
from lightly_studio.services.annotations_service.update_annotation import (
    update_annotation,
)
from lightly_studio.services.annotations_service.update_annotation_bounding_box import (
    update_annotation_bounding_box,
)
from lightly_studio.services.annotations_service.update_annotation_label import (
    update_annotation_label,
)
from lightly_studio.services.annotations_service.update_annotations import (
    update_annotations,
)
from lightly_studio.services.annotations_service.update_segmentation_mask import (
    update_segmentation_mask,
)

__all__ = [
    "create_annotation",
    "delete_annotation",
    "get_annotation_by_id",
    "update_annotation",
    "update_annotation_bounding_box",
    "update_annotation_label",
    "update_annotations",
    "update_segmentation_mask",
]
