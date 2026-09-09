"""Indexing MCAP point-cloud frames as locator samples for the labeling workspace.

Recordings are far too large to keep in the repository, so pass one in:

    make start-e2e-mcap-point-cloud MCAP_PATH=/absolute/path/to/perception.mcap
"""

from environs import Env
from mcap.reader import make_reader

import lightly_studio as ls
from lightly_studio.core.mcap import recording_index

env = Env()
env.read_env()
recording_path = env.path("MCAP_PATH")
max_frames = env.int("MCAP_MAX_FRAMES", 200)
selected_topic = env.str("MCAP_TOPIC", default=None)

if not recording_path.is_file():
    raise ValueError(
        f"No MCAP recording at {recording_path}. Pass one with "
        "make start-e2e-mcap-point-cloud MCAP_PATH=/absolute/path/to/recording.mcap"
    )

# Cleanup an existing database
ls.db_manager.connect(cleanup_existing=True)

with recording_path.open("rb") as stream:
    reader = make_reader(stream)
    channels = recording_index.find_point_cloud_channels(reader)
    if not channels:
        raise ValueError(f"{recording_path} has no ROS 2 CDR PointCloud2 channels.")

    for channel in channels:
        print(f"{channel.topic} (channel {channel.channel_id}, {channel.message_count} messages)")

    selected = next(
        (channel for channel in channels if channel.topic == selected_topic), channels[0]
    )
    dataset = ls.GroupDataset.create(components=[("lidar", ls.SampleType.MCAP)])
    indexed = 0
    first_group = None
    for frame in recording_index.iter_point_cloud_frames(
        reader, topic=selected.topic, limit=max_frames
    ):
        group = dataset.add_group_sample(components={"lidar": frame})
        first_group = first_group or group
        indexed += 1

print(f"Indexed {indexed} frames from {selected.topic}.")

if first_group is not None:
    lidar = first_group["lidar"]
    assert lidar is not None
    # The labeling workspace is not linked from the navigation yet, so print the route.
    print(
        "\nOpen the labeling workspace at:\n"
        f"  /datasets/{dataset.collection_id}/point-clouds/{lidar.collection_id}"
        f"/{lidar.sample_id}?collection_type=mcap&group_id={first_group.sample_id}"
    )

ls.start_gui()
