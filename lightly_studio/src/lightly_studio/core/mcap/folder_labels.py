"""Match annotation MCAPs in a folder to indexed recordings."""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass
from uuid import UUID

from sqlmodel import Session

from lightly_studio.core.file_outcome_report import MissingInputFileError
from lightly_studio.core.mcap import add_mcaps, annotation_mcap
from lightly_studio.dataset import fsspec_lister
from lightly_studio.resolvers import mcap_group_sequence_resolver

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _IndexedSequence:
    """The sequence that holds the groups of one recording."""

    sample_id: UUID
    recording_id: UUID


def annotation_mcap_uris(path: str, suffix: str) -> list[str]:
    """List annotation MCAPs under a folder."""
    return [
        uri
        for uri in fsspec_lister.iter_files_from_path(
            path=path, allowed_extensions=add_mcaps.MCAP_EXTENSIONS
        )
        if annotation_mcap.is_annotation_mcap(uri=uri, suffix=suffix)
    ]


def recording_index(
    session: Session, dataset_id: UUID
) -> tuple[dict[str, _IndexedSequence], dict[str, list[_IndexedSequence]]]:
    """Map normalized recording URIs and file names to their sequences."""
    by_uri: dict[str, _IndexedSequence] = {}
    by_file_name: dict[str, list[_IndexedSequence]] = defaultdict(list)
    rows = mcap_group_sequence_resolver.get_all_by_dataset_id(
        session=session, dataset_id=dataset_id
    )
    for row in rows:
        sequence = _IndexedSequence(sample_id=row.sample_id, recording_id=row.recording_id)
        uri = annotation_mcap.normalized_uri(row.uri)
        by_uri[uri] = sequence
        by_file_name[uri.rsplit("/", maxsplit=1)[-1]].append(sequence)
    return by_uri, dict(by_file_name)


def match_sequence(
    annotation_uri: str,
    suffix: str,
    by_uri: dict[str, _IndexedSequence],
    by_file_name: dict[str, list[_IndexedSequence]],
) -> _IndexedSequence:
    """Join an annotation MCAP to one indexed sequence.

    The recording URI is the annotation URI with the suffix removed. When that URI is
    not indexed, a unique recording file name matches instead.

    Raises:
        MissingInputFileError: If no single indexed recording matches.
    """
    recording_uri = annotation_mcap.recording_uri_from_annotation_mcap(
        uri=annotation_uri, suffix=suffix
    )
    sequence = by_uri.get(recording_uri)
    if sequence is not None:
        return sequence
    file_name = recording_uri.rsplit("/", maxsplit=1)[-1]
    matches = by_file_name.get(file_name, [])
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        logger.warning(
            "Annotation MCAP '%s' matches %d recordings named '%s'.",
            annotation_uri,
            len(matches),
            file_name,
        )
        raise MissingInputFileError(
            f"Annotation MCAP '{annotation_uri}' matches {len(matches)} "
            f"recordings named '{file_name}'."
        )
    logger.warning("No indexed recording for annotation MCAP '%s'.", annotation_uri)
    raise MissingInputFileError(f"No indexed recording for annotation MCAP '{annotation_uri}'.")
