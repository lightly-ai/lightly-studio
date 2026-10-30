"""Writes and uploads SceneUpdate annotation files for one or many sequences."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from uuid import UUID

import fsspec
from fsspec.implementations.local import LocalFileSystem
from mcap.exceptions import McapError
from sqlmodel import Session

from lightly_studio.core.mcap import annotation_mcap, write_scene_update_mcap
from lightly_studio.core.mcap.errors import McapAccessError
from lightly_studio.errors import ExportError
from lightly_studio.export import mcap_sequence_messages
from lightly_studio.models.recording import RecordingTable
from lightly_studio.resolvers import (
    annotation_resolver,
    mcap_group_sequence_resolver,
    recording_resolver,
)
from lightly_studio.services.recording_service import reader_cache


def common_reference_frame_ids(session: Session, sequence_ids: Sequence[UUID]) -> list[str]:
    """Returns the reference frames every sequence's recording has in common.

    Args:
        session: The database session.
        sequence_ids: The sequences to intersect. An empty sequence gives `[]`.

    Returns:
        The frames of the first sequence's recording that every other recording also
        has, kept in the first recording's order.
    """
    if not sequence_ids:
        return []
    frame_lists = [
        _sequence_recording(session=session, sequence_id=sequence_id).reference_frame_ids
        for sequence_id in sequence_ids
    ]
    first_frame_ids, other_frame_sets = frame_lists[0], [set(frames) for frames in frame_lists[1:]]
    return [
        frame_id
        for frame_id in first_frame_ids
        if all(frame_id in frame_set for frame_set in other_frame_sets)
    ]


def export_frame_ids(session: Session, sequence_ids: Sequence[UUID]) -> list[str]:
    """Returns the coordinate frames the cuboids of the sequences can be exported in.

    The frames the cuboids are stored in come first, ordered by cuboid count
    descending, then by name. They need no transform. The common reference frames
    that are not listed yet come next, in the order of `common_reference_frame_ids`.

    Args:
        session: The database session.
        sequence_ids: The sequences to export. An empty sequence gives `[]`.

    Returns:
        The frame IDs, without duplicates and without empty IDs.
    """
    stored_frame_ids = annotation_resolver.get_cuboid_frame_ids_by_sequence_ids(
        session=session, sequence_ids=sequence_ids
    )
    reference_frame_ids = common_reference_frame_ids(session=session, sequence_ids=sequence_ids)
    return stored_frame_ids + [
        frame_id for frame_id in reference_frame_ids if frame_id not in stored_frame_ids
    ]


def write_annotation_files(  # noqa: PLR0913
    session: Session,
    sequence_ids: Sequence[UUID],
    annotation_collection_id: UUID,
    target_frame_id: str,
    local_dir: Path,
    topic: str = annotation_mcap.DEFAULT_SCENE_UPDATE_TOPIC,
    suffix: str = annotation_mcap.DEFAULT_ANNOTATION_MCAP_SUFFIX,
) -> list[Path]:
    """Writes one SceneUpdate annotation file per sequence into `local_dir`.

    Every file name is checked for clashes before anything is written. A later
    failure, e.g. a missing transform in the second sequence, leaves the files of the
    sequences before it in `local_dir`.

    Args:
        session: The database session.
        sequence_ids: The sequences to export. Must not be empty.
        annotation_collection_id: The annotation source to export cuboids from.
        target_frame_id: The coordinate frame every cuboid is mapped into.
        local_dir: The directory to write the annotation files into. Must already exist.
        topic: The topic to write the SceneUpdate messages on.
        suffix: Inserted before the `.mcap` extension of the source recording's name.

    Returns:
        The written file paths, in `sequence_ids` order.

    Raises:
        ExportError: If `sequence_ids` is empty, a sequence has no recording, two
            sequences would write to the same file name, the metadata of a recording
            cannot be read, or the cuboids of a sequence cannot be exported.
    """
    if not sequence_ids:
        raise ExportError("No sequences to export.")
    recordings = [
        _sequence_recording(session=session, sequence_id=sequence_id)
        for sequence_id in sequence_ids
    ]
    file_names = [
        annotation_mcap.annotation_mcap_file_name(recording_uri=recording.uri, suffix=suffix)
        for recording in recordings
    ]
    _check_no_name_clash(sequence_ids=sequence_ids, file_names=file_names)

    return [
        _write_annotation_file(
            session=session,
            sequence_id=sequence_id,
            recording=recording,
            annotation_collection_id=annotation_collection_id,
            target_frame_id=target_frame_id,
            local_path=local_dir / file_name,
            topic=topic,
        )
        for sequence_id, recording, file_name in zip(sequence_ids, recordings, file_names)
    ]


def upload(local_paths: Sequence[Path], output_dir: str) -> list[str]:
    """Uploads local files to a local or remote directory, never overwriting one.

    Args:
        local_paths: The local files to upload.
        output_dir: The destination directory, with or without a trailing slash. Any
            fsspec protocol works, e.g. a local path or `s3://bucket/prefix`.

    Returns:
        The destination URIs, in `local_paths` order.

    Raises:
        ExportError: If a destination has another protocol than `output_dir`, e.g. for
            `s3://` without a bucket, or any destination already exists. Nothing is
            uploaded then. A missing local `output_dir` is created after these checks
            pass. Also raised if a destination cannot be checked or written. The files
            uploaded before a failed write are removed again, so a retry does not fail
            on them. The error names any file that cannot be removed.
    """
    prefix = output_dir.rstrip("/")
    destinations = [f"{prefix}/{local_path.name}" for local_path in local_paths]
    _check_same_protocol(output_dir=output_dir, destinations=destinations)
    existing = [destination for destination in destinations if _destination_exists(destination)]
    if existing:
        raise ExportError(f"Destination(s) already exist: {', '.join(existing)}")

    _create_local_output_dir(output_dir=prefix)
    for index, (local_path, destination) in enumerate(zip(local_paths, destinations)):
        try:
            _put_file(local_path=local_path, destination=destination)
        except ExportError as error:
            # The failed destination may hold a partial file, so it is removed too.
            leftovers = _remove_destinations(destinations=destinations[: index + 1])
            if leftovers:
                raise ExportError(
                    f"{error} These files could not be removed and must be deleted by "
                    f"hand: {', '.join(leftovers)}"
                ) from error
            raise
    return destinations


def _sequence_recording(session: Session, sequence_id: UUID) -> RecordingTable:
    """Returns the recording of an MCAP sequence.

    Raises:
        ExportError: If the sequence has no MCAP recording.
    """
    mcap_sequence = mcap_group_sequence_resolver.get_by_id(session=session, sample_id=sequence_id)
    if mcap_sequence is None:
        raise ExportError(f"Sequence {sequence_id} has no MCAP recording.")
    recording = recording_resolver.get_by_id(
        session=session, recording_id=mcap_sequence.recording_id
    )
    if recording is None:
        raise ExportError(f"Recording {mcap_sequence.recording_id} not found.")
    return recording


def _check_no_name_clash(sequence_ids: Sequence[UUID], file_names: Sequence[str]) -> None:
    """Raises `ExportError` naming the first two sequences that share a file name."""
    sequence_id_by_file_name: dict[str, UUID] = {}
    for sequence_id, file_name in zip(sequence_ids, file_names):
        clashing_sequence_id = sequence_id_by_file_name.get(file_name)
        if clashing_sequence_id is not None:
            raise ExportError(
                f"Sequences {clashing_sequence_id} and {sequence_id} both map to file name "
                f"'{file_name}'."
            )
        sequence_id_by_file_name[file_name] = sequence_id


def _write_annotation_file(  # noqa: PLR0913
    session: Session,
    sequence_id: UUID,
    recording: RecordingTable,
    annotation_collection_id: UUID,
    target_frame_id: str,
    local_path: Path,
    topic: str,
) -> Path:
    """Writes one sequence's SceneUpdate annotation file to `local_path`."""
    messages = mcap_sequence_messages.build_sequence_messages(
        session=session,
        recording=recording,
        sequence_id=sequence_id,
        annotation_collection_id=annotation_collection_id,
        target_frame_id=target_frame_id,
    )
    try:
        with reader_cache.borrow_reader(uri=recording.uri) as reader:
            metadata_records = reader.get_metadata_records()
    except (OSError, McapError, McapAccessError) as e:
        raise ExportError(f"Cannot read the metadata of recording {recording.uri}: {e}") from e
    with local_path.open("wb") as output:
        write_scene_update_mcap.write_scene_update_mcap(
            output=output,
            messages=messages,
            frame_id=target_frame_id,
            topic=topic,
            metadata_records=metadata_records,
        )
    return local_path


def _check_same_protocol(output_dir: str, destinations: Sequence[str]) -> None:
    """Raises `ExportError` if a destination resolves to another filesystem.

    For example, `"s3://"` has no bucket: its destinations start with `s3:/`, which
    fsspec resolves to the local filesystem.
    """
    protocol = fsspec.utils.get_protocol(output_dir)
    for destination in destinations:
        if fsspec.utils.get_protocol(destination) != protocol:
            raise ExportError(
                f"Cannot write {destination}: the output folder {output_dir} is not valid."
            )


def _put_file(local_path: Path, destination: str) -> None:
    """Uploads one local file to a local or remote destination URI.

    Raises:
        ExportError: If the destination cannot be written.
    """
    try:
        fs, fs_path = fsspec.core.url_to_fs(url=destination)
        fs.put_file(str(local_path), fs_path)
    except OSError as e:
        raise ExportError(f"Cannot write {destination}: {e}") from e


def _create_local_output_dir(output_dir: str) -> None:
    """Creates a missing output folder, only on the local filesystem.

    Other filesystems are left alone: S3 needs no folders, and `makedirs` of s3fs can
    try to create buckets.
    """
    fs, fs_path = fsspec.core.url_to_fs(url=output_dir)
    if isinstance(fs, LocalFileSystem):
        fs.makedirs(fs_path, exist_ok=True)


def _destination_exists(destination: str) -> bool:
    """Returns whether a local or remote destination URI already exists.

    Raises:
        ExportError: If the destination cannot be checked.
    """
    try:
        fs, fs_path = fsspec.core.url_to_fs(url=destination)
        return bool(fs.exists(fs_path))
    except OSError as e:
        raise ExportError(f"Cannot check whether {destination} exists: {e}") from e


def _remove_destinations(destinations: Sequence[str]) -> list[str]:
    """Removes uploaded destinations and returns the ones that could not be removed.

    A destination that does not exist counts as removed.
    """
    leftovers = []
    for destination in destinations:
        fs, fs_path = fsspec.core.url_to_fs(url=destination)
        try:
            fs.rm_file(fs_path)
        except FileNotFoundError:
            pass
        except OSError:
            leftovers.append(destination)
    return leftovers
