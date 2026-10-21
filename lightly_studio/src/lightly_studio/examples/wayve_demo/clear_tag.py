"""Remove a tag from every sample of a demo dataset.

Run from `lightly_studio/` with the venv from the README. Refresh the GUI after it:

    python src/lightly_studio/examples/wayve_demo/clear_tag.py clips filter_v1
    python src/lightly_studio/examples/wayve_demo/clear_tag.py frames examples
"""

from __future__ import annotations

import sys
from collections.abc import Iterable

import lightly_studio as ls
from lightly_studio.core.sample import Sample
from lightly_studio.examples.wayve_demo import config

USAGE = "Usage: clear_tag.py <clips|frames> <tag>"


def main() -> None:
    """Remove the tag given on the command line and print the sample count."""
    if len(sys.argv) != 3 or sys.argv[1] not in ("clips", "frames"):  # noqa: PLR2004
        sys.exit(USAGE)
    dataset_kind, tag = sys.argv[1], sys.argv[2]
    config.connect()
    samples: Iterable[Sample] = (
        ls.VideoDataset.load(name=config.CLIPS_DATASET)
        if dataset_kind == "clips"
        else ls.ImageDataset.load(name=config.FRAMES_DATASET)
    )
    count = clear_tag(samples=samples, tag=tag)
    print(f"Removed tag '{tag}' from {count} samples")


def clear_tag(samples: Iterable[Sample], tag: str) -> int:
    """Remove the tag from every sample that has it.

    Returns:
        The number of samples that lost the tag.
    """
    count = 0
    for sample in samples:
        if tag in sample.tags:
            sample.remove_tag(name=tag)
            count += 1
    return count


if __name__ == "__main__":
    main()
