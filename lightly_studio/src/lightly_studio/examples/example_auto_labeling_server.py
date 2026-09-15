"""Run LightlyStudio against a registered SAM3 annotation server.

Usage::

    uv run src/lightly_studio/examples/example_auto_labeling_server.py \
        --annotation-url http://localhost:8080 \
        --images datasets/coco_subset_128_images/images

The server must implement the protocol in ``prototype/auto-labeling/PROTOCOL.md``.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import requests

import lightly_studio as ls
from lightly_studio.database import db_manager


def main() -> None:
    """Register the annotation server, create an image dataset, and start the GUI."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--annotation-url", required=True, help="SAM3 server base URL")
    parser.add_argument("--annotation-api-key", default=None, help="Optional server Bearer key")
    parser.add_argument("--images", type=Path, required=True, help="Directory of images")
    parser.add_argument("--port", type=int, default=8001)
    args = parser.parse_args()

    os.environ["LIGHTLY_STUDIO_ANNOTATION_URL"] = args.annotation_url.rstrip("/")
    if args.annotation_api_key:
        os.environ["LIGHTLY_STUDIO_ANNOTATION_API_KEY"] = args.annotation_api_key

    headers = (
        {"Authorization": f"Bearer {args.annotation_api_key}"} if args.annotation_api_key else {}
    )
    response = requests.get(
        f"{args.annotation_url.rstrip('/')}/v1/describe",
        headers=headers,
        timeout=5,
    )
    response.raise_for_status()
    descriptor = response.json()
    if not descriptor.get("ready"):
        raise RuntimeError("The annotation server is reachable but SAM3 is not ready.")
    print(f"Registered {descriptor['model_key']} at {args.annotation_url}")

    db_manager.connect(cleanup_existing=True)
    dataset = ls.ImageDataset.create()
    dataset.add_images_from_path(path=args.images)
    ls.start_gui(port=args.port, open_browser=True)


if __name__ == "__main__":
    main()
