"""Shared helpers of the tests that export MCAP cuboids."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from sqlmodel import Session

from lightly_studio.core.mcap import add_labels, add_mcaps
from lightly_studio.core.mcap.mcap_dataset import McapDataset
from lightly_studio.core.mcap.sequence import McapSequence
from lightly_studio.core.mcap.type_definitions import CuboidLabel
from lightly_studio.models.annotation_label import AnnotationLabelCreate
from lightly_studio.models.collection import CollectionTable
from lightly_studio.models.recording import RecordingTable
from lightly_studio.resolvers import (
    annotation_label_resolver,
    annotation_resolver,
    collection_resolver,
    recording_resolver,
)
from tests.core.mcap import helpers
from tests.core.mcap.test_add_mcaps import COMPONENTS, MAX_PAIRING_DIFF_NS, POINT_CLOUD_COMPONENT
from tests.helpers_resolvers import cuboid_create


def index_recording(
    tmp_path: Path,
    base_link_poses: tuple[tuple[int, tuple[float, float, float]], ...] = (),
) -> tuple[McapDataset, McapSequence, list[UUID]]:
    """Indexes a test recording and returns its dataset, sequence and tick group sample IDs."""
    mcap_path = helpers.write_mcap(tmp_path / "recording.mcap", base_link_poses=base_link_poses)
    dataset = McapDataset.create(components=COMPONENTS, name="perception")
    add_mcaps.index_recording(
        dataset=dataset,
        mcap_path=str(mcap_path),
        sync_component=POINT_CLOUD_COMPONENT,
        components=COMPONENTS,
        max_pairing_diff_ns=MAX_PAIRING_DIFF_NS,
    )
    sequence = dataset.get_sequences()[0]
    group_ids = [entry.sample_id for entry in sequence.get_samples()]
    return dataset, sequence, group_ids


def recording(session: Session, sequence: McapSequence) -> RecordingTable:
    """Returns the recording the sequence was indexed from."""
    result = recording_resolver.get_by_id(session=session, recording_id=sequence.recording_id)
    assert result is not None
    return result


def annotation_collection(session: Session, dataset: McapDataset, name: str) -> CollectionTable:
    """Returns the annotation collection of the dataset with the given name."""
    collections = collection_resolver.get_annotation_collections(
        session=session, parent_collection_id=dataset.group_dataset.collection_id
    )
    return next(collection for collection in collections if collection.name == name)


def cuboid(  # noqa: PLR0913
    timestamp_ns: int,
    track_id: int,
    frame_id: str = "odom",
    px: float = 4.0,
    py: float = 0.0,
    pz: float = 0.5,
    parent_track_id: int | None = None,
    interpolated: bool = False,
) -> CuboidLabel:
    """Returns a `truck` cuboid label."""
    return CuboidLabel(
        timestamp_ns=timestamp_ns,
        frame_id=frame_id,
        class_name="truck",
        track_id=track_id,
        parent_track_id=parent_track_id,
        interpolated=interpolated,
        position=(px, py, pz),
        rotation=(0.0, 0.0, 0.0, 1.0),
        size=(2.0, 1.0, 1.5),
    )


def create_cuboid_annotation(
    session: Session, dataset: McapDataset, parent_sample_id: UUID, object_track_id: UUID | None
) -> UUID:
    """Stores a `truck` cuboid in frame `odom` in the default annotation source."""
    label = annotation_label_resolver.create(
        session=session,
        label=AnnotationLabelCreate(dataset_id=dataset.dataset_id, annotation_label_name="truck"),
    )
    return annotation_resolver.create_many(
        session=session,
        parent_collection_id=dataset.group_dataset.collection_id,
        collection_name=add_labels.DEFAULT_ANNOTATION_SOURCE,
        annotations=[
            cuboid_create(
                parent_sample_id=parent_sample_id,
                annotation_label_id=label.annotation_label_id,
                object_track_id=object_track_id,
                px=4.0,
            )
        ],
    )[0]
