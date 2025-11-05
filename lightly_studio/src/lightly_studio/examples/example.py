"""Example of how to load samples from path with the dataset class."""

from io import BytesIO

import av
import fsspec

import lightly_studio as ls
from lightly_studio import db_manager
from lightly_studio.models.dataset import SampleType
from lightly_studio.resolvers import (
    video_frame_resolver,
    video_resolver,
)

# Cleanup an existing database
db_manager.connect(cleanup_existing=True)

# Define the path to the dataset directory

# Create a DatasetLoader from a path
dataset = ls.Dataset.create(sample_type=SampleType.VIDEO, name="My Video Dataset")
dataset.add_videos_from_path(
    path="C:\\Users\\horatiu\\Videos\\webcam_app_old_impl.mp4",
    allowed_extensions=[".mp4"],
    embed=False,
    fps=2,
)
videos = video_resolver.get_all_by_dataset_id(
    session=db_manager.persistent_session(), dataset_id=dataset.dataset_id
)
# Print out all samples in the dataset
for video in videos.samples:
    print(video)
    video_frames = video_frame_resolver.get_all_by_dataset_id(
        session=db_manager.persistent_session(),
        dataset_id=dataset.dataset_id,
        video_sample_ids=[video.sample_id],
    )
    video_frames_list = []
    for frame in video_frames.samples:
        print(frame)
        video_frames_list.append(frame.frame_number)

    # Open video with PyAV
    fs, fs_path = fsspec.core.url_to_fs(video.file_path_abs)
    content = fs.cat_file(fs_path)
    video_buffer = BytesIO(content)
    container = av.open(video_buffer)
    video_stream = container.streams.video[0]
    frames = []

    try:
            # Get video stream properties once
            framerate = float(video_stream.average_rate) if video_stream.average_rate else 30.0
            time_base = video_stream.time_base

            # Sort frame numbers for more efficient sequential processing
            sorted_frame_numbers = sorted(video_frames_list)

            # Reset to beginning and decode frames sequentially
            container.seek(0, backward=True, stream=video_stream)

            target_frame_iter = iter(sorted_frame_numbers)
            next_target = next(target_frame_iter, None)

            # Decode frames sequentially and save target frames
            for current_frame_idx, frame in enumerate(container.decode(video_stream)):
                if next_target is None:
                    # All target frames processed
                    break

                if current_frame_idx == next_target:
                    # This is a target frame, save it
                    frame.to_image().save(f"D:\\tmp\\frame-{current_frame_idx:04d}.jpg")
                    # Get next target frame
                    next_target = next(target_frame_iter, None)

                # If we've passed all remaining targets, we can stop
                if next_target is not None and current_frame_idx > sorted_frame_numbers[-1]:
                    break

    finally:
            # Always close the container
            container.close()

for sample in dataset:
    print(sample)

ls.start_gui()
