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
# A full recording holds tens of thousands of frames, and walking to them decompresses the
# chunks on the way. Index the channel's opening seconds by default so the example finishes
# quickly whatever the recording's length; raise either bound to cover more of the timeline,
# or set the window to 0 to be bounded by the frame count alone.
max_frames = env.int("EXAMPLES_MCAP_MAX_FRAMES", 200)
max_seconds = env.float("EXAMPLES_MCAP_MAX_SECONDS", 2.0)
selected_topic = env.str("EXAMPLES_MCAP_TOPIC", default=None)
duration_ns = int(max_seconds * 1_000_000_000) if max_seconds > 0 else None

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
        reader, topic=selected.topic, limit=max_frames, duration_ns=duration_ns
    ):
        dataset.add_group_sample(components={"lidar": frame})
        indexed += 1

window = f"the first {max_seconds:g} s of " if duration_ns is not None else ""
print(f"\nIndexed {indexed} point-cloud frames from {window}{selected.topic}.")

ls.start_gui()
