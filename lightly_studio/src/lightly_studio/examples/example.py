"""Example of how to load samples from path with the dataset class."""

from io import BytesIO

import av
import fsspec

import lightly_studio as ls
from lightly_studio import db_manager
from lightly_studio.models.dataset import SampleType
from lightly_studio.resolvers import (
    dataset_resolver,
    video_frame_resolver,
    video_resolver,
)

# Cleanup an existing database
db_manager.connect(cleanup_existing=True)

# Define the path to the dataset directory

# Create a DatasetLoader from a path
dataset = ls.Dataset.create(sample_type=SampleType.VIDEO, name="My Video Dataset")
dataset.add_videos_from_path(
    path="/Users/leonardo/Downloads/phys101/small/",
    allowed_extensions=[".mov"],
)
# videos = video_resolver.get_all_by_dataset_id(
#     session=db_manager.persistent_session(), dataset_id=dataset.dataset_id
# )
# # Print out all samples in the dataset
# video_frame_dataset = dataset_resolver.get_or_create_video_frame_child(
#     session=db_manager.persistent_session(),
#     dataset_id=dataset.dataset_id,
# )
# for video in videos.samples:
#     print(video)
# video_frames = video_frame_resolver.get_all_by_dataset_id(
#     session=db_manager.persistent_session(),
#     dataset_id=video_frame_dataset,
# )
# video_frames_list = []
# for frame in video_frames.samples:
#     print(frame)

ls.start_gui()