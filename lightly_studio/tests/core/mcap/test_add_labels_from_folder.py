from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

import pytest
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.core.file_outcome_report import MissingInputFileError
from lightly_studio.core.mcap import add_mcaps, annotation_mcap
from lightly_studio.core.mcap.folder_labels import (
    _IndexedSequence,
    annotation_mcap_uris,
    match_sequence,
    recording_index,
)
from lightly_studio.core.mcap.mcap_dataset import McapDataset
from lightly_studio.database import db_manager
from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.collection import SampleType
from lightly_studio.models.recording import RecordingFormat
from lightly_studio.resolvers import (
    annotation_resolver,
    mcap_group_sequence_resolver,
    recording_resolver,
)
from tests.core.mcap import helpers
from tests.core.mcap.test_add_mcaps import COMPONENTS, MAX_PAIRING_DIFF_NS, POINT_CLOUD_COMPONENT
from tests.helpers_resolvers import create_collection


def test_annotation_mcap_uris(tmp_path: Path) -> None:
    (tmp_path / "a_labeled.mcap").write_bytes(b"")
    (tmp_path / "b.mcap").write_bytes(b"")

    found = annotation_mcap_uris(path=str(tmp_path), suffix="_labeled")

    assert [Path(uri).name for uri in found] == ["a_labeled.mcap"]


def test_recording_index(db_session: Session) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.SEQUENCE)
    recording_id = recording_resolver.create(
        session=db_session,
        dataset_id=collection.dataset_id,
        uri="C:\\bags\\drive.mcap",
        format_=RecordingFormat.MCAP,
    )
    sample_id = mcap_group_sequence_resolver.create(
        session=db_session,
        collection_id=collection.collection_id,
        recording_id=recording_id,
    )

    by_uri, by_file_name = recording_index(session=db_session, dataset_id=collection.dataset_id)

    sequence = _IndexedSequence(sample_id=sample_id, recording_id=recording_id)
    assert by_uri == {"C:/bags/drive.mcap": sequence}
    assert by_file_name == {"drive.mcap": [sequence]}


def test_match_sequence__exact_uri() -> None:
    sequence = _IndexedSequence(sample_id=uuid4(), recording_id=uuid4())

    matched = match_sequence(
        annotation_uri="s3://bucket/runs/foo_labeled.mcap",
        suffix="_labeled",
        by_uri={"s3://bucket/runs/foo.mcap": sequence},
        by_file_name={},
    )

    assert matched is sequence


def test_match_sequence__file_name() -> None:
    sequence = _IndexedSequence(sample_id=uuid4(), recording_id=uuid4())

    matched = match_sequence(
        annotation_uri="s3://labels/foo_labeled.mcap",
        suffix="_labeled",
        by_uri={},
        by_file_name={"foo.mcap": [sequence]},
    )

    assert matched is sequence


def test_match_sequence__ambiguous_file_name() -> None:
    sequences = [
        _IndexedSequence(sample_id=uuid4(), recording_id=uuid4()),
        _IndexedSequence(sample_id=uuid4(), recording_id=uuid4()),
    ]

    with pytest.raises(MissingInputFileError, match="matches 2 recordings"):
        match_sequence(
            annotation_uri="s3://labels/foo_labeled.mcap",
            suffix="_labeled",
            by_uri={},
            by_file_name={"foo.mcap": sequences},
        )


def test_match_sequence__missing() -> None:
    with pytest.raises(MissingInputFileError, match="No indexed recording"):
        match_sequence(
            annotation_uri="s3://labels/foo_labeled.mcap",
            suffix="_labeled",
            by_uri={},
            by_file_name={},
        )


def test_add_labels_from_folder__skips_a_second_call(
    patch_collection: None,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    dataset, group_ids = _index(tmp_path)
    _write_labels(tmp_path / "recording.mcap")
    dataset.add_labels_from_folder(path=tmp_path, topic="/scene_update")
    dataset.add_labels_from_folder(path=tmp_path, topic="/scene_update")
    assert len(_cuboids(group_ids)) == 1


def test_add_labels_from_folder__logs_unknown_topic(
    patch_collection: None,  # noqa: ARG001
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    dataset, group_ids = _index(tmp_path)
    _write_labels(tmp_path / "recording.mcap")

    dataset.add_labels_from_folder(path=tmp_path, topic="/wrong_topic")

    assert "Topic '/wrong_topic' is not in annotation MCAP" in caplog.text
    assert "SceneUpdate topics in the file: /scene_update" in caplog.text
    assert _cuboids(group_ids) == []


def test_add_labels_from_folder__warns_when_dataset_has_no_recordings(
    patch_collection: None,  # noqa: ARG001
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    dataset = McapDataset.create(components=COMPONENTS, name="perception")

    dataset.add_labels_from_folder(path=tmp_path, topic="/scene_update")

    assert "Dataset 'perception' has no indexed recordings to add labels to." in caplog.text


def test_add_labels_from_folder__warns_without_annotation_files(
    patch_collection: None,  # noqa: ARG001
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    dataset, _ = _index(tmp_path)

    dataset.add_labels_from_folder(path=tmp_path, topic="/scene_update")

    assert "No annotation MCAPs named '<recording>_labeled.mcap'" in caplog.text


def test_add_labels_from_folder__logs_file_that_is_not_an_mcap(
    patch_collection: None,  # noqa: ARG001
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    dataset, _ = _index(tmp_path)
    (tmp_path / "recording_labeled.mcap").write_text("not an mcap")

    dataset.add_labels_from_folder(path=tmp_path, topic="/scene_update")

    assert "Cannot add annotations from" in caplog.text


def test_add_labels_from_folder__logs_missing_annotation_file(
    patch_collection: None,  # noqa: ARG001
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    mocker: MockerFixture,
) -> None:
    dataset, _ = _index(tmp_path)
    missing = annotation_mcap.annotation_mcap_uri(recording_uri=str(tmp_path / "recording.mcap"))
    mocker.patch(
        "lightly_studio.core.mcap.folder_labels.annotation_mcap_uris",
        return_value=[missing],
    )

    dataset.add_labels_from_folder(path=tmp_path, topic="/scene_update")

    assert f"Cannot add annotations from '{missing}': the file does not exist." in caplog.text


def _index(tmp_path: Path) -> tuple[McapDataset, list[UUID]]:
    path = helpers.write_mcap(tmp_path / "recording.mcap")
    dataset = McapDataset.create(components=COMPONENTS, name="perception")
    add_mcaps.index_recording(
        dataset=dataset,
        mcap_path=str(path),
        sync_component=POINT_CLOUD_COMPONENT,
        components=COMPONENTS,
        max_pairing_diff_ns=MAX_PAIRING_DIFF_NS,
    )
    sequence = dataset.get_sequences()[0]
    return dataset, [entry.sample_id for entry in sequence.get_samples()]


def _cuboids(parent_sample_ids: list[UUID]) -> list[object]:
    return list(
        annotation_resolver.get_all_by_parent_sample_ids(
            session=db_manager.persistent_session(),
            parent_sample_ids=parent_sample_ids,
            annotation_types=[AnnotationType.CUBOID_3D],
        )
    )


def _write_labels(source_path: Path) -> None:
    timestamp_ns = helpers.LIDAR_LOG_TIMES_NS[0]
    sec, nsec = divmod(timestamp_ns, 1_000_000_000)
    helpers.write_json_mcap(
        path=Path(annotation_mcap.annotation_mcap_uri(recording_uri=str(source_path))),
        topic="/scene_update",
        schema_name="foxglove_msgs/msg/SceneUpdate",
        messages=[(timestamp_ns, {"entities": [_entity(sec, nsec)]})],
    )


def _entity(sec: int, nsec: int) -> dict[str, object]:
    return {
        "id": "truck_1",
        "timestamp": {"sec": sec, "nsec": nsec},
        "frame_id": "odom",
        "metadata": [{"key": "class", "value": "truck"}, {"key": "track_id", "value": "1"}],
        "cubes": [
            {
                "pose": {
                    "position": {"x": 1.0, "y": 0.0, "z": 0.0},
                    "orientation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0},
                },
                "size": {"x": 1.0, "y": 1.0, "z": 1.0},
            }
        ],
    }
