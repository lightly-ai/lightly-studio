"""Example of indexing MCAP point-cloud frames as locator samples.

An MCAP sample is a seek key, not a point cloud: a channel id and a log time naming one
message inside a recording. This script walks a recording's index, finds the ROS 2
`sensor_msgs/msg/PointCloud2` channels, and creates one group per frame pointing at it.
Nothing is decoded here. The browser decodes frames itself, reading byte ranges of the
recording through ``/mcap/media/{sample_id}``.

Run it against a recording:

    EXAMPLES_MCAP_PATH=/absolute/path/to/perception.mcap \
    LIGHTLY_STUDIO_POINT_CLOUD_ENABLED=1 \
    LIGHTLY_STUDIO_MCAP_RECORDING_PATH=/absolute/path/to/perception.mcap \
        uv run src/lightly_studio/examples/example_mcap_point_cloud.py

``LIGHTLY_STUDIO_MCAP_RECORDING_PATH`` is what the media endpoint serves. It is a
development-only stand-in until recording paths are stored per recording; see
lightly_studio/core/mcap/recording_source.py.
"""

from environs import Env
from mcap.reader import make_reader

import lightly_studio as ls
from lightly_studio.core.mcap import recording_index

env = Env()
env.read_env()
recording_path = env.path("EXAMPLES_MCAP_PATH")
# A full recording holds tens of thousands of frames. Index a slice by default so the
# example finishes quickly; raise it to cover more of the timeline.
max_frames = env.int("EXAMPLES_MCAP_MAX_FRAMES", 200)
selected_topic = env.str("EXAMPLES_MCAP_TOPIC", default=None)

ls.db_manager.connect(cleanup_existing=True)

with recording_path.open("rb") as stream:
    reader = make_reader(stream)
    channels = recording_index.find_point_cloud_channels(reader)
    if not channels:
        raise ValueError(f"{recording_path} has no ROS 2 CDR PointCloud2 channels.")

    print("Point-cloud channels in this recording:")
    for channel in channels:
        print(f"  {channel.topic} (channel {channel.channel_id}, {channel.message_count} messages)")

    selected = next(
        (channel for channel in channels if channel.topic == selected_topic), channels[0]
    )
    print(f"\nIndexing {selected.topic} as locator samples.")

    dataset = ls.GroupDataset.create(components=[("lidar", ls.SampleType.MCAP)])
    indexed = 0
    for frame in recording_index.iter_point_cloud_frames(
        reader, topic=selected.topic, limit=max_frames
    ):
        dataset.add_group_sample(components={"lidar": frame})
        indexed += 1

print(f"\nIndexed {indexed} point-cloud frames from {selected.topic}.")

ls.start_gui()
