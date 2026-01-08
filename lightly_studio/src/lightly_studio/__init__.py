# Set up logging before importing any other modules.
# Add noqa to silence unused import and unsorted imports linter warnings.
from . import setup_logging  # noqa: F401 I001

# Import db_manager for SQLModel to discover db models.
from lightly_studio import db_manager  # noqa: F401

from lightly_studio.core.image_dataset import ImageDataset
from lightly_studio.core.video_dataset import VideoDataset
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
    "ImageDataset",
    "SampleType",
    "VideoDataset",
    "start_gui",
    "start_gui_background",
    "stop_gui_background",
]
