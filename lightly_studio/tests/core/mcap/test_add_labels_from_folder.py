from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from sqlmodel import Session

from lightly_studio.core.file_outcome_report import MissingInputFileError
from lightly_studio.core.mcap.folder_labels import (
    _IndexedSequence,
    annotation_mcap_uris,
    match_sequence,
    recording_index,
)
from lightly_studio.models.collection import SampleType
from lightly_studio.models.recording import RecordingFormat
from lightly_studio.resolvers import mcap_group_sequence_resolver, recording_resolver
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
