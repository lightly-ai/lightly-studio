r"""Prints camera-frame URLs for every video channel in an MCAP file.

Usage::

    uv run python src/lightly_studio/scripts/demo_mcap_urls.py \
        <mcap_path> <host> <port> <dataset_id> <recording_id>
"""

from __future__ import annotations

import sys

from lightly_studio.core.mcap.reader import McapFileReader
from lightly_studio.core.mcap.topic_kind import TopicKind

_ARGC = 6


def main() -> None:
    """Prints camera-frame URLs for every video channel in an MCAP file."""
    if len(sys.argv) != _ARGC:
        print("Usage: demo_mcap_urls.py <mcap_path> <host> <port> <dataset_id> <recording_id>")
        sys.exit(1)

    mcap_path, host, port, dataset_id, recording_id = sys.argv[1:]
    base = f"http://{host}:{port}"

    with McapFileReader(mcap_path) as reader:
        video_topics = [t for t in reader.get_topics() if t.kind == TopicKind.VIDEO]
        if not video_topics:
            print("No video topics found in the MCAP file.")
            return

        reader.load_data_for_topics(topics=[t.name for t in video_topics])

        print()
        print("Camera-frame URLs — open in a browser or: curl -o frame.jpg '<url>'")
        print()
        for topic in video_topics:
            locators = reader.get_frame_locators(topic.name)
            kf = next(
                (loc for loc in locators if loc.keyframe_log_time_ns == loc.log_time_ns),
                None,
            )
            if kf is None:
                continue
            url = (
                f"{base}/datasets/{dataset_id}/recordings/{recording_id}/camera-frame"
                f"?channel_id={kf.channel_id}&keyframe_timestamp_ns={kf.log_time_ns}"
                f"&w=640"
            )
            print(f"  {topic.name}")
            print(f"  {url}")
            print()


if __name__ == "__main__":
    main()
