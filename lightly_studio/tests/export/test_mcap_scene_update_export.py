from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path
from uuid import UUID, uuid4

import fsspec
import pytest
from fsspec.implementations.memory import MemoryFileSystem
from mcap.reader import make_reader
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.core.mcap import add_labels
from lightly_studio.core.mcap.annotation_mcap import DEFAULT_SCENE_UPDATE_TOPIC
from lightly_studio.core.mcap.type_definitions import SceneUpdateLabels
from lightly_studio.database import db_manager
from lightly_studio.errors import ExportError
from lightly_studio.export import mcap_scene_update_export
from lightly_studio.resolvers import recording_resolver
from tests.core.mcap import helpers
from tests.export import mcap_helpers

METADATA_RECORDS = (("rosbag2", {"serialized_metadata": "x"}),)


@pytest.fixture(autouse=True)
def _clear_memory_fs() -> Iterator[None]:
    """Clears the fsspec in-memory filesystem before and after each test."""
    fsspec.filesystem("memory").store.clear()
    yield
    fsspec.filesystem("memory").store.clear()


def test_common_reference_frame_ids(
    patch_collection: None,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    _, sequence_a, _ = mcap_helpers.index_recording(
        tmp_path=tmp_path / "a", metadata_records=METADATA_RECORDS, dataset_name="perception_a"
    )
    _, sequence_b, _ = mcap_helpers.index_recording(
        tmp_path=tmp_path / "b", metadata_records=METADATA_RECORDS, dataset_name="perception_b"
    )
    session = db_manager.persistent_session()
    recording_a = recording_resolver.get_by_id(
        session=session, recording_id=sequence_a.recording_id
    )
    recording_b = recording_resolver.get_by_id(
        session=session, recording_id=sequence_b.recording_id
    )
    assert recording_a is not None
    assert recording_b is not None
    recording_a.reference_frame_ids = ["map", "base_link"]
    recording_b.reference_frame_ids = ["base_link", "map", "x"]
    session.add(recording_a)
    session.add(recording_b)
    session.commit()

    result = mcap_scene_update_export.common_reference_frame_ids(
        session=session, sequence_ids=[sequence_a.sample_id, sequence_b.sample_id]
    )

    assert result == ["map", "base_link"]


def test_common_reference_frame_ids__empty_input(db_session: Session) -> None:
    result = mcap_scene_update_export.common_reference_frame_ids(
        session=db_session, sequence_ids=[]
    )

    assert result == []


def test_export_frame_ids(
    patch_collection: None,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    dataset, sequence, _ = mcap_helpers.index_recording(
        tmp_path=tmp_path, metadata_records=METADATA_RECORDS
    )
    timestamp_ns = helpers.LIDAR_LOG_TIMES_NS[0]
    add_labels.write_sequence_labels(
        dataset=dataset,
        sequence=sequence,
        annotation_mcap_uri="memory://ground_truth_labeled.mcap",
        messages=[
            (
                timestamp_ns,
                SceneUpdateLabels(
                    cuboids=(
                        mcap_helpers.cuboid(timestamp_ns=timestamp_ns, track_id=7, frame_id="odom"),
                    )
                ),
            )
        ],
    )
    session = db_manager.persistent_session()
    _set_reference_frame_ids(
        session=session, recording_id=sequence.recording_id, frame_ids=["base_link"]
    )

    result = mcap_scene_update_export.export_frame_ids(
        session=session, sequence_ids=[sequence.sample_id]
    )

    assert result == ["odom", "base_link"]


def test_export_frame_ids__ordered_by_cuboid_count(
    patch_collection: None,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    dataset, sequence, _ = mcap_helpers.index_recording(
        tmp_path=tmp_path, metadata_records=METADATA_RECORDS
    )
    first_ns, second_ns = helpers.LIDAR_LOG_TIMES_NS
    add_labels.write_sequence_labels(
        dataset=dataset,
        sequence=sequence,
        annotation_mcap_uri="memory://ground_truth_labeled.mcap",
        messages=[
            (
                first_ns,
                SceneUpdateLabels(
                    cuboids=(
                        mcap_helpers.cuboid(timestamp_ns=first_ns, track_id=7, frame_id="odom"),
                        mcap_helpers.cuboid(
                            timestamp_ns=first_ns, track_id=8, frame_id="base_link"
                        ),
                    )
                ),
            ),
            (
                second_ns,
                SceneUpdateLabels(
                    cuboids=(
                        mcap_helpers.cuboid(
                            timestamp_ns=second_ns, track_id=8, frame_id="base_link"
                        ),
                    )
                ),
            ),
        ],
    )
    session = db_manager.persistent_session()
    _set_reference_frame_ids(
        session=session, recording_id=sequence.recording_id, frame_ids=["map", "base_link"]
    )

    result = mcap_scene_update_export.export_frame_ids(
        session=session, sequence_ids=[sequence.sample_id]
    )

    # 2 cuboids in "base_link", 1 in "odom", then the reference frames not listed yet.
    assert result == ["base_link", "odom", "map"]


def test_export_frame_ids__no_cuboids(
    patch_collection: None,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    _, sequence, _ = mcap_helpers.index_recording(
        tmp_path=tmp_path, metadata_records=METADATA_RECORDS
    )
    session = db_manager.persistent_session()
    _set_reference_frame_ids(
        session=session, recording_id=sequence.recording_id, frame_ids=["map", "base_link"]
    )

    result = mcap_scene_update_export.export_frame_ids(
        session=session, sequence_ids=[sequence.sample_id]
    )

    assert result == ["map", "base_link"]


def test_write_annotation_files__one_file_per_sequence(
    patch_collection: None,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    dataset, sequence, _ = mcap_helpers.index_recording(
        tmp_path=tmp_path, metadata_records=METADATA_RECORDS
    )
    session = db_manager.persistent_session()
    timestamp_ns = helpers.LIDAR_LOG_TIMES_NS[0]
    add_labels.write_sequence_labels(
        dataset=dataset,
        sequence=sequence,
        annotation_mcap_uri="memory://ground_truth_labeled.mcap",
        messages=[
            (
                timestamp_ns,
                SceneUpdateLabels(
                    cuboids=(mcap_helpers.cuboid(timestamp_ns=timestamp_ns, track_id=7),)
                ),
            )
        ],
    )
    ground_truth = mcap_helpers.annotation_collection(
        session=session, dataset=dataset, name=add_labels.DEFAULT_ANNOTATION_SOURCE
    )
    local_dir = tmp_path / "out"
    local_dir.mkdir()

    result = mcap_scene_update_export.write_annotation_files(
        session=session,
        sequence_ids=[sequence.sample_id],
        annotation_collection_id=ground_truth.collection_id,
        target_frame_id="odom",
        local_dir=local_dir,
    )

    assert result == [local_dir / "recording_labeled.mcap"]
    messages = add_labels.read_scene_updates(str(result[0]), DEFAULT_SCENE_UPDATE_TOPIC)
    assert len(messages) == 2

    with result[0].open("rb") as stream:
        reader = make_reader(stream)
        records = [(record.name, dict(record.metadata)) for record in reader.iter_metadata()]
    assert records == list(METADATA_RECORDS)


def test_write_annotation_files__no_sequences_fails(db_session: Session, tmp_path: Path) -> None:
    with pytest.raises(ExportError, match=r"No sequences to export\."):
        mcap_scene_update_export.write_annotation_files(
            session=db_session,
            sequence_ids=[],
            annotation_collection_id=uuid4(),
            target_frame_id="odom",
            local_dir=tmp_path,
        )


def test_write_annotation_files__name_clash_fails(
    patch_collection: None,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    session = db_manager.persistent_session()
    _, sequence_a, _ = mcap_helpers.index_recording(
        tmp_path=tmp_path / "a", metadata_records=METADATA_RECORDS, dataset_name="perception_a"
    )
    _, sequence_b, _ = mcap_helpers.index_recording(
        tmp_path=tmp_path / "b", metadata_records=METADATA_RECORDS, dataset_name="perception_b"
    )
    local_dir = tmp_path / "out"
    local_dir.mkdir()

    # The name clash is found before any sequence is read, so a made-up annotation
    # collection id is enough; `build_sequence_messages` is never called.
    with pytest.raises(ExportError, match=r"recording_labeled\.mcap"):
        mcap_scene_update_export.write_annotation_files(
            session=session,
            sequence_ids=[sequence_a.sample_id, sequence_b.sample_id],
            annotation_collection_id=uuid4(),
            target_frame_id="odom",
            local_dir=local_dir,
        )

    assert list(local_dir.iterdir()) == []


def test_write_annotation_files__missing_recording_file_fails(
    patch_collection: None,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    _, sequence, _ = mcap_helpers.index_recording(
        tmp_path=tmp_path, metadata_records=METADATA_RECORDS
    )
    session = db_manager.persistent_session()
    recording = recording_resolver.get_by_id(session=session, recording_id=sequence.recording_id)
    assert recording is not None
    missing_uri = str(tmp_path / "missing.mcap")
    recording.uri = missing_uri
    session.add(recording)
    session.commit()
    local_dir = tmp_path / "out"
    local_dir.mkdir()

    # The sequence has no cuboids, so only the metadata read opens the recording.
    with pytest.raises(ExportError, match=re.escape(missing_uri)):
        mcap_scene_update_export.write_annotation_files(
            session=session,
            sequence_ids=[sequence.sample_id],
            annotation_collection_id=uuid4(),
            target_frame_id="odom",
            local_dir=local_dir,
        )


def test_upload__writes_to_prefix(tmp_path: Path) -> None:
    local_path = tmp_path / "recording_labeled.mcap"
    local_path.write_bytes(b"mcap-bytes")

    result = mcap_scene_update_export.upload(
        local_paths=[local_path], output_dir="memory://bucket/out"
    )

    assert result == ["memory://bucket/out/recording_labeled.mcap"]
    assert fsspec.filesystem("memory").cat("bucket/out/recording_labeled.mcap") == b"mcap-bytes"


def test_upload__prefix_with_trailing_slash(tmp_path: Path) -> None:
    local_path = tmp_path / "recording_labeled.mcap"
    local_path.write_bytes(b"mcap-bytes")

    result = mcap_scene_update_export.upload(
        local_paths=[local_path], output_dir="memory://bucket/out/"
    )

    assert result == ["memory://bucket/out/recording_labeled.mcap"]


def test_upload__creates_missing_local_dir(tmp_path: Path) -> None:
    local_path = tmp_path / "recording_labeled.mcap"
    local_path.write_bytes(b"mcap-bytes")
    output_dir = tmp_path / "new" / "out"

    result = mcap_scene_update_export.upload(local_paths=[local_path], output_dir=str(output_dir))

    assert result == [f"{output_dir}/recording_labeled.mcap"]
    assert (output_dir / "recording_labeled.mcap").read_bytes() == b"mcap-bytes"


def test_upload__existing_file_fails(tmp_path: Path) -> None:
    filesystem = fsspec.filesystem("memory")
    filesystem.pipe("bucket/out/recording_labeled.mcap", b"existing-bytes")
    local_path = tmp_path / "recording_labeled.mcap"
    local_path.write_bytes(b"new-bytes")

    with pytest.raises(ExportError, match=r"recording_labeled\.mcap"):
        mcap_scene_update_export.upload(local_paths=[local_path], output_dir="memory://bucket/out")

    assert filesystem.cat("bucket/out/recording_labeled.mcap") == b"existing-bytes"


def test_upload__protocol_without_path_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    local_path = tmp_path / "in" / "recording_labeled.mcap"
    local_path.parent.mkdir()
    local_path.write_bytes(b"mcap-bytes")
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)

    # "s3://" without a bucket must not fall back to a local "s3:" folder.
    with pytest.raises(ExportError, match=r"s3://"):
        mcap_scene_update_export.upload(local_paths=[local_path], output_dir="s3://")

    assert list(cwd.iterdir()) == []


def test_upload__write_error_names_destination(tmp_path: Path, mocker: MockerFixture) -> None:
    local_path = tmp_path / "recording_labeled.mcap"
    local_path.write_bytes(b"mcap-bytes")
    mocker.patch.object(MemoryFileSystem, "put_file", side_effect=PermissionError("denied"))

    with pytest.raises(ExportError, match=r"memory://bucket/out/recording_labeled\.mcap: denied"):
        mcap_scene_update_export.upload(local_paths=[local_path], output_dir="memory://bucket/out")


def test_upload__write_error_removes_uploaded_files(tmp_path: Path, mocker: MockerFixture) -> None:
    local_paths = [tmp_path / "a_labeled.mcap", tmp_path / "b_labeled.mcap"]
    for local_path in local_paths:
        local_path.write_bytes(b"mcap-bytes")
    put_file = MemoryFileSystem.put_file

    def _fail_on_b(self: MemoryFileSystem, lpath: str, rpath: str, **kwargs: object) -> None:
        if rpath.endswith("b_labeled.mcap"):
            raise PermissionError("denied")
        put_file(self, lpath, rpath, **kwargs)

    mocker.patch.object(MemoryFileSystem, "put_file", autospec=True, side_effect=_fail_on_b)

    with pytest.raises(ExportError, match=r"b_labeled\.mcap: denied$"):
        mcap_scene_update_export.upload(local_paths=local_paths, output_dir="memory://bucket/out")

    assert not fsspec.filesystem("memory").exists("bucket/out/a_labeled.mcap")


def test_upload__write_error_names_files_not_removed(tmp_path: Path, mocker: MockerFixture) -> None:
    local_paths = [tmp_path / "a_labeled.mcap", tmp_path / "b_labeled.mcap"]
    for local_path in local_paths:
        local_path.write_bytes(b"mcap-bytes")
    put_file = MemoryFileSystem.put_file

    def _fail_on_b(self: MemoryFileSystem, lpath: str, rpath: str, **kwargs: object) -> None:
        if rpath.endswith("b_labeled.mcap"):
            raise PermissionError("denied")
        put_file(self, lpath, rpath, **kwargs)

    mocker.patch.object(MemoryFileSystem, "put_file", autospec=True, side_effect=_fail_on_b)
    mocker.patch.object(MemoryFileSystem, "rm_file", side_effect=PermissionError("denied"))

    with pytest.raises(ExportError, match=r"deleted by hand: memory://bucket/out/a_labeled\.mcap"):
        mcap_scene_update_export.upload(local_paths=local_paths, output_dir="memory://bucket/out")


def _set_reference_frame_ids(session: Session, recording_id: UUID, frame_ids: list[str]) -> None:
    recording = recording_resolver.get_by_id(session=session, recording_id=recording_id)
    assert recording is not None
    recording.reference_frame_ids = frame_ids
    session.add(recording)
    session.commit()
