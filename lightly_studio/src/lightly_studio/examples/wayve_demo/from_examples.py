"""Tag the frames that look most like a few example frames.

Tag 3 to 5 frames `examples` in the GUI first. The script scores every frame by its
embedding similarity to the examples and tags the 50 best frames `from_examples`.
"""

from __future__ import annotations

import os
import sys

import lightly_studio as ls
from lightly_studio.core.dataset_query import ImageSampleField, OrderByMetadataField
from lightly_studio.database import db_manager

DB_URL = os.environ.get("WAYVE_DB_URL", "postgresql://lightly:lightly@localhost:5434/wayve")
EXAMPLES_TAG = "examples"
TAG = "from_examples"
TOP = 50


def main() -> None:
    """Score the frames against the examples and tag the best frames."""
    db_manager.connect(db_url=DB_URL)
    frames = ls.ImageDataset.load(name="nexar-frames")
    try:
        frames.compute_similarity_metadata(
            query_tag_name=EXAMPLES_TAG, metadata_name="similarity_examples"
        )
    except ValueError as error:
        if str(error) != "Query tag not found":
            raise
        sys.exit(f"No tag '{EXAMPLES_TAG}'. Tag 3-5 frames '{EXAMPLES_TAG}' in the GUI first.")

    # Remove the tag first, so that a second run gives the same result.
    for frame in frames.query().match(ImageSampleField.tags.contains(TAG)).to_list():
        frame.remove_tag(name=TAG)

    best = frames.query().order_by(OrderByMetadataField("similarity_examples").desc())
    best.slice(limit=TOP).add_tag(tag_name=TAG)
    print(f"Tagged the {TOP} best frames with '{TAG}'")


if __name__ == "__main__":
    main()
