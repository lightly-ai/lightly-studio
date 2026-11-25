from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from sqlmodel import Session

from lightly_studio.core.mcap import add_labels, add_mcaps
from lightly_studio.core.mcap.mcap_dataset import McapDataset
from lightly_studio.core.mcap.sequence import McapSequence
from lightly_studio.core.mcap.type_definitions import SceneUpdateLabels
from lightly_studio.database import db_manager
from lightly_studio.resolvers import annotation_resolver
from tests import helpers_resolvers
from tests.core.mcap import helpers
from tests.core.mcap.test_add_mcaps import COMPONENTS, MAX_PAIRING_DIFF_NS, POINT_CLOUD_COMPONENT
from tests.export import mcap_helpers


def _index_two_sequences(tmp_path: Path) -> tuple[McapDataset, McapSequence, McapSequence]:
    """Indexes two recordings into one dataset and returns it with both sequences."""
    dataset, first, _ = mcap_helpers.index_recording(tmp_path=tmp_path / "first")
    second_path = tmp_path / "second"
    second_path.mkdir()
    add_mcaps.index_recording(
        session=db_manager.persistent_session(),
        collection_id=dataset.collection_id,
        mcap_path=str(helpers.write_mcap(second_path / "second.mcap")),
        sync_component=POINT_CLOUD_COMPONENT,
        components=COMPONENTS,
        max_pairing_diff_ns=MAX_PAIRING_DIFF_NS,
    )
    second = next(
        sequence for sequence in dataset.get_sequences() if sequence.sample_id != first.sample_id
    )
    return dataset, first, second


def _write_cuboids(
    dataset: McapDataset, sequence: McapSequence, per_tick: tuple[int, int], source: str
) -> None:
    """Writes `per_tick[i]` cuboids on the i-th tick of the sequence."""
    messages = [
        (
            timestamp_ns,
            SceneUpdateLabels(
                cuboids=tuple(
                    mcap_helpers.cuboid(timestamp_ns=timestamp_ns, track_id=track_id)
                    for track_id in range(count)
                )
            ),
        )
        for timestamp_ns, count in zip(helpers.LIDAR_LOG_TIMES_NS, per_tick, strict=True)
        if count
    ]
    add_labels.write_sequence_labels(
        dataset=dataset,
        sequence=sequence,
        annotation_mcap_uri=f"memory://{source}.mcap",
        messages=messages,
        annotation_source=source,
    )


def test_count_objects_by_sample_ids__sequences_count_cuboids_on_their_ticks(
    patch_collection: None,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    dataset, first, second = _index_two_sequences(tmp_path=tmp_path)
    # 2 cuboids of the same tracks on the first tick and 1 on the second: 3 cuboids, not 2 tracks.
    _write_cuboids(
        dataset=dataset,
        sequence=first,
        per_tick=(2, 1),
        source=add_labels.DEFAULT_ANNOTATION_SOURCE,
    )

    result = annotation_resolver.count_objects_by_sample_ids(
        session=db_manager.persistent_session(),
        collection_id=dataset.collection_id,
        sample_ids=[first.sample_id, second.sample_id],
    )

    assert result == {first.sample_id: 3, second.sample_id: 0}


def test_count_objects_by_sample_ids__all_annotation_sources_count(
    patch_collection: None,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    dataset, first, _ = _index_two_sequences(tmp_path=tmp_path)
    _write_cuboids(
        dataset=dataset,
        sequence=first,
        per_tick=(1, 1),
        source=add_labels.DEFAULT_ANNOTATION_SOURCE,
    )
    _write_cuboids(dataset=dataset, sequence=first, per_tick=(1, 0), source="predictions")

    result = annotation_resolver.count_objects_by_sample_ids(
        session=db_manager.persistent_session(),
        collection_id=dataset.collection_id,
        sample_ids=[first.sample_id],
    )

    assert result == {first.sample_id: 3}


def test_count_objects_by_sample_ids__images_count_their_own_annotations(
    db_session: Session,
) -> None:
    dataset = helpers_resolvers.create_collection(session=db_session)
    images = helpers_resolvers.create_images(
        db_session=db_session,
        collection_id=dataset.collection_id,
        images=[helpers_resolvers.ImageStub(path=f"{index}.png") for index in range(3)],
    )
    label = helpers_resolvers.create_annotation_label(
        session=db_session, root_collection_id=dataset.collection_id
    )
    for image, count in zip(images, (2, 1, 0), strict=True):
        for _ in range(count):
            helpers_resolvers.create_annotation(
                session=db_session,
                collection_id=dataset.collection_id,
                sample_id=image.sample_id,
                annotation_label_id=label.annotation_label_id,
            )

    result = annotation_resolver.count_objects_by_sample_ids(
        session=db_session,
        collection_id=dataset.collection_id,
        sample_ids=[image.sample_id for image in images],
    )

    assert result == {images[0].sample_id: 2, images[1].sample_id: 1, images[2].sample_id: 0}


def test_count_objects_by_sample_ids__samples_outside_the_collection_count_zero(
    db_session: Session,
) -> None:
    dataset = helpers_resolvers.create_collection(session=db_session)
    other = helpers_resolvers.create_collection(session=db_session)
    image = helpers_resolvers.create_image(session=db_session, collection_id=other.collection_id)
    label = helpers_resolvers.create_annotation_label(
        session=db_session, root_collection_id=other.collection_id
    )
    helpers_resolvers.create_annotation(
        session=db_session,
        collection_id=other.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
    )
    unknown = uuid4()

    result = annotation_resolver.count_objects_by_sample_ids(
        session=db_session,
        collection_id=dataset.collection_id,
        sample_ids=[image.sample_id, unknown],
    )

    assert result == {image.sample_id: 0, unknown: 0}


def test_count_objects_by_sample_ids__empty(db_session: Session) -> None:
    dataset = helpers_resolvers.create_collection(session=db_session)

    result = annotation_resolver.count_objects_by_sample_ids(
        session=db_session, collection_id=dataset.collection_id, sample_ids=[]
    )

    assert result == {}
