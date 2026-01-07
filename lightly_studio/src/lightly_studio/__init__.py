# Set up logging before importing any other modules.
# Add noqa to silence unused import and unsorted imports linter warnings.
from . import setup_logging  # noqa: F401 I001
from lightly_studio.core.image_dataset import ImageDataset as Dataset
from lightly_studio.core.start_gui import (
    check_gui_background,
    start_gui,
    start_gui_background,
    stop_gui_background,
)
from lightly_studio.models.collection import SampleType


# TODO (Jonas 08/25): This will be removed as soon as the new interface is used in the examples
from lightly_studio.models.annotation.annotation_base import AnnotationType

__all__ = [
    "AnnotationType",
    "Dataset",
    "SampleType",
    "check_gui_background",
    "start_gui",
    "start_gui_background",
    "stop_gui_background",
]
