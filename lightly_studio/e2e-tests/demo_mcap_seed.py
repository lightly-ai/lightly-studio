"""Demo seed script for testing point-cloud labeling with a local MCAP file.

Usage (via Makefile):

    make demo-mcap-server FLOCI_MCAP_FILES=/path/to/perception.mcap

Or manually:

    # 1. Start Floci and upload the MCAP file:
    make setup-floci FLOCI_MCAP_FILES=/path/to/perception.mcap

    # 2. Run this script:
    LIGHTLY_STUDIO_POINT_CLOUD_ENABLED=true uv run e2e-tests/demo_mcap_seed.py

The script reads channel metadata from the MCAP file in Floci (no pixel data is
loaded), creates the full DB schema, and starts the GUI on port 8001.

Collection hierarchy created:

    SEQUENCE (root, dataset root)
    └── GROUP
        └── MCAP slots (one per camera/lidar topic)
"""

from __future__ import annotations

import os
import sys

import lightly_studio as ls
from lightly_studio.core.mcap import topic_kind as topic_kind_module
from lightly_studio.core.mcap.reader import McapFileReader
from lightly_studio.core.mcap.topic_kind import TopicKind
from lightly_studio.database import db_manager
from lightly_studio.models.collection import CollectionCreate, SampleType
from lightly_studio.models.mcap_group_component_definition import McapDataType
from lightly_studio.models.recording import RecordingFormat
from lightly_studio.resolvers import (
    collection_resolver,
    mcap_group_component_definition_resolver,
    mcap_group_sequence_resolver,
    recording_resolver,
)

MCAP_S3_URI = os.environ.get(
    "DEMO_MCAP_S3_URI",
    "s3://lightly-studio/recordings/perception.mcap",
)
DEMO_PORT = int(os.environ.get("DEMO_PORT", "8001"))
DEMO_HOST = os.environ.get("DEMO_HOST", "127.0.0.1")
DATASET_NAME = "demo-mcap"


def _mcap_data_type(kind: TopicKind) -> McapDataType | None:
    if kind in (TopicKind.VIDEO, TopicKind.IMAGE):
        return McapDataType.VIDEO_FRAME
    if kind == TopicKind.POINT_CLOUD:
        return McapDataType.POINT_CLOUD
    return None


def seed() -> None:
    """Creates the MCAP demo dataset in the database and prints the workspace URL."""
    print(f"Reading MCAP topics from {MCAP_S3_URI} ...")
    with McapFileReader(path=MCAP_S3_URI) as reader:
        topics = reader.get_topics()

    slots: list[tuple[str, McapDataType, int]] = []
    for topic in topics:
        kind = topic_kind_module.from_schema_name(schema_name=topic.schema_name)
        data_type = _mcap_data_type(kind=kind)
        if data_type is None:
            continue
        slot_name = topic.name.lstrip("/").replace("/", "_")
        slots.append((slot_name, data_type, topic.channel_id))

    if not slots:
        print(
            "ERROR: No camera or lidar topics found in the MCAP file.\n"
            "Expected CompressedVideo, CompressedImage, PointCloud, or PointCloud2 topics.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Found {len(slots)} slot(s): {[s[0] for s in slots]}")

    session = db_manager.persistent_session()

    # SEQUENCE collection is the dataset root.
    sequence_collection = collection_resolver.create(
        session=session,
        collection=CollectionCreate(name=DATASET_NAME, sample_type=SampleType.SEQUENCE),
    )
    dataset_id = sequence_collection.dataset_id

    # GROUP child holds the per-topic MCAP component slots.
    group_collection = collection_resolver.create(
        session=session,
        collection=CollectionCreate(
            name=f"{DATASET_NAME}_group",
            parent_collection_id=sequence_collection.collection_id,
            sample_type=SampleType.GROUP,
        ),
    )

    # MCAP component slots under the GROUP collection.
    mcap_components = [(slot_name, SampleType.MCAP) for slot_name, _, _ in slots]
    slot_collections = collection_resolver.create_group_components(
        session=session,
        parent_collection_id=group_collection.collection_id,
        components=mcap_components,
    )
    for slot_name, data_type, channel_id in slots:
        mcap_group_component_definition_resolver.create(
            session=session,
            collection_id=slot_collections[slot_name].collection_id,
            mcap_data_type=data_type,
            channel_id=channel_id,
        )

    recording_id = recording_resolver.create(
        session=session,
        dataset_id=dataset_id,
        uri=MCAP_S3_URI,
        format_=RecordingFormat.MCAP,
    )
    print(f"Registered recording  (recording_id={recording_id})")

    sample_id = mcap_group_sequence_resolver.create(
        session=session,
        collection_id=sequence_collection.collection_id,
        recording_id=recording_id,
    )
    print(f"Created sequence sample (sample_id={sample_id})")

    print(
        f"\nOpen the point-cloud workspace at:\n"
        f"  http://{DEMO_HOST}:{DEMO_PORT}"
        f"/datasets/{dataset_id}"
        f"/point-clouds/{sequence_collection.collection_id}"
        f"/{sample_id}\n"
    )


if __name__ == "__main__":
    ls.db_manager.connect(cleanup_existing=True)
    seed()
    ls.start_gui(host=DEMO_HOST, port=DEMO_PORT)
