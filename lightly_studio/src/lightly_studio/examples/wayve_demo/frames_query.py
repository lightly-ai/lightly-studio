"""The near-miss filter: tag the frames where a vehicle is close.

A vehicle box that fills 13% of the frame or more means that the vehicle is close.
Edit the query during the demo, then run the script again and refresh the GUI.
"""

from __future__ import annotations

import os

import lightly_studio as ls
from lightly_studio.core.dataset_query import AND, ImageSampleField
from lightly_studio.database import db_manager

DB_URL = os.environ.get("WAYVE_DB_URL", "postgresql://lightly:lightly@localhost:5434/wayve")
TAG = "close_vehicle"

QUERY = AND(
    ImageSampleField.metadata["max_vehicle_area"] >= 0.13,  # noqa: PLR2004
    # ImageSampleField.metadata["light_conditions"] == "Dark",
)


def main() -> None:
    """Replace the tag with the frames that match the query."""
    db_manager.connect(db_url=DB_URL)
    frames = ls.ImageDataset.load(name="nexar-frames")

    # Remove the tag first, so that a second run gives the same result.
    for frame in frames.query().match(ImageSampleField.tags.contains(TAG)).to_list():
        frame.remove_tag(name=TAG)

    matches = frames.query().match(QUERY)
    matches.add_tag(tag_name=TAG)
    print(f"Tagged {len(matches.to_list())} frames with '{TAG}'")


if __name__ == "__main__":
    main()
