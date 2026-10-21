"""Tag the frames that look most like a few example frames.

Tag 3 to 5 frames in the GUI first, by default with the tag `examples`. The script scores
every frame by embedding similarity to the examples and tags the top frames.

Run from `lightly_studio/` with the venv from the README. Refresh the GUI after it:

    python src/lightly_studio/examples/wayve_demo/from_examples.py
    python src/lightly_studio/examples/wayve_demo/from_examples.py --examples-tag dark --top 20
"""

from __future__ import annotations

import argparse
import sys

import lightly_studio as ls
from lightly_studio.core.dataset_query import OrderByMetadataField
from lightly_studio.examples.wayve_demo import clear_tag, config

TAG = "from_examples"
METADATA_NAME = "similarity_examples"


def main() -> None:
    """Score the frames against the examples and tag the top frames."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--examples-tag", default="examples")
    parser.add_argument("--top", type=int, default=50)
    args = parser.parse_args()

    config.connect()
    frames = ls.ImageDataset.load(name=config.FRAMES_DATASET)
    try:
        frames.compute_similarity_metadata(
            query_tag_name=args.examples_tag, metadata_name=METADATA_NAME
        )
    except ValueError as error:
        if str(error) != "Query tag not found":
            raise
        sys.exit(
            f"Tag '{args.examples_tag}' not found on {config.FRAMES_DATASET}. "
            f"Select 3-5 frames in the GUI and tag them '{args.examples_tag}'."
        )

    clear_tag.clear_tag(samples=frames, tag=TAG)
    top = frames.query().order_by(OrderByMetadataField(METADATA_NAME).desc()).slice(limit=args.top)
    top.add_tag(tag_name=TAG)
    print(f"Tagged the top {len(top.to_list())} frames with '{TAG}'")


if __name__ == "__main__":
    main()
