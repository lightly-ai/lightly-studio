# Set up logging before importing any other modules.
# Add noqa to silence unused import and unsorted imports linter warnings.
from . import setup_logging  # noqa: F401 I001

# Import db_manager for SQLModel to discover db models.
from lightly_studio.database import db_manager  # noqa: F401

# Import utils to expose utility functions at the package level.
from lightly_studio import utils  # noqa: F401

from lightly_studio.core.image.image_dataset import ImageDataset
from lightly_studio.core.video.video_dataset import VideoDataset
from lightly_studio.core.video.video_frame_dataset import VideoFrameDataset
from lightly_studio.core.video.video_frame_sample import VideoFrameSample
from lightly_studio.core.group.group_dataset import GroupDataset
from lightly_studio.core.image.create_image import CreateImage
from lightly_studio.core.video.create_video import CreateVideo
from lightly_studio.core.start_gui import (
    start_gui,
    start_gui_background,
    stop_gui_background,
)
from lightly_studio.dataset.embedding_generator import (
    EmbeddingGenerator,
    ImageCrop,
    ImageEmbeddingGenerator,
    VideoEmbeddingGenerator,
)
from lightly_studio.dataset.embedding_manager import set_default_embedding_model
from lightly_studio.models.collection import SampleType
from lightly_studio.enterprise import connect
from lightly_studio.core.lightly_train_helpers.generate_train_script import lt_train_script


# TODO (Jonas 08/25): This will be removed as soon as the new interface is used in the examples
from lightly_studio.models.annotation.annotation_base import AnnotationType

__all__ = [
    "AnnotationType",
    "CreateImage",
    "CreateVideo",
    "EmbeddingGenerator",
    "GroupDataset",
    "ImageCrop",
    "ImageDataset",
    "ImageEmbeddingGenerator",
    "SampleType",
    "VideoDataset",
    "VideoEmbeddingGenerator",
    "VideoFrameDataset",
    "VideoFrameSample",
    "connect",
    "lt_train_script",
    "set_default_embedding_model",
    "start_gui",
    "start_gui_background",
    "stop_gui_background",
]
