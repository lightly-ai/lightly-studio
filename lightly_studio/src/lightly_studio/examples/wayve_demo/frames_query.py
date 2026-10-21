"""Tag the frames that match a metadata query.

Edit the query at the top of `main()` during the demo, then run the script again.

Run from `lightly_studio/` with the venv from the README. Refresh the GUI after it:

    python src/lightly_studio/examples/wayve_demo/frames_query.py
"""

from __future__ import annotations

import lightly_studio as ls
from lightly_studio.core.dataset_query import AND, ImageSampleField
from lightly_studio.examples.wayve_demo import clear_tag, config

TAG = "dark_close_vehicle"


def main() -> None:
    """Replace the tag with the frames that match the query and print the count."""
    query = AND(
        ImageSampleField.metadata["light_conditions"] == "Dark",
        ImageSampleField.metadata["max_vehicle_area"] >= 0.13,  # noqa: PLR2004
    )

    config.connect()
    frames = ls.ImageDataset.load(name=config.FRAMES_DATASET)
    clear_tag.clear_tag(samples=frames, tag=TAG)
    matches = frames.query().match(query)
    matches.add_tag(tag_name=TAG)
    print(f"Tagged {len(matches.to_list())} frames with '{TAG}'")


if __name__ == "__main__":
    main()
