# Set up logging before importing any other modules.
# Add noqa to silence unused import and unsorted imports linter warnings.
from . import setup_logging  # noqa: F401 I001
from lightly_studio.core.dataset import Dataset
from lightly_studio.core.start_gui import start_gui

# TODO (Jonas 08/25): This will be removed as soon as the new interface is used in the examples
from lightly_studio.dataset.loader import DatasetLoader
from lightly_studio.models.annotation.annotation_base import AnnotationType

__all__ = ["AnnotationType", "Dataset", "DatasetLoader", "start_gui"]
