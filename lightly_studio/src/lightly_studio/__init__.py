# Set up logging before importing any other modules.
# Add noqa to silence unused import and unsorted imports linter warnings.
from . import setup_logging  # noqa: F401 I001

# Import db_manager for SQLModel to discover db models.
from lightly_studio import db_manager  # noqa: F401

from lightly_studio.core.image.image_dataset import ImageDataset
from lightly_studio.core.video.video_dataset import VideoDataset
from lightly_studio.core.group.group_dataset import GroupDataset
from lightly_studio.core.image.create_image import CreateImage
from lightly_studio.core.video.create_video import CreateVideo
from lightly_studio.core.start_gui import (
    start_gui,
    start_gui_background,
    stop_gui_background,
)
from lightly_studio.models.collection import SampleType


# TODO (Jonas 08/25): This will be removed as soon as the new interface is used in the examples
from lightly_studio.models.annotation.annotation_base import AnnotationType

__all__ = [
    "AnnotationType",
    "CreateImage",
    "CreateVideo",
    "GroupDataset",
    "ImageDataset",
    "SampleType",
    "VideoDataset",
    "start_gui",
    "start_gui_background",
    "stop_gui_background",
]
