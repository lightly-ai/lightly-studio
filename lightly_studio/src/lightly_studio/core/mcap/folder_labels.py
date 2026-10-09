"""Match annotation MCAPs in a folder to indexed recordings."""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

from mcap.exceptions import McapError
from sqlmodel import Session

from lightly_studio.core.file_outcome_report import (
    AlreadyPresentInputFileError,
    BrokenInputFileError,
    FileOutcomeReport,
    MissingInputFileError,
)
from lightly_studio.core.mcap import add_labels, add_mcaps, annotation_mcap
from lightly_studio.core.mcap.errors import McapAccessError
from lightly_studio.core.mcap.sequence import McapSequence
from lightly_studio.dataset import fsspec_lister
from lightly_studio.resolvers import (
    annotation_collection_coverage_resolver,
    collection_resolver,
    mcap_group_sequence_resolver,
)
from lightly_studio.type_definitions import PathLike

if TYPE_CHECKING:
    from lightly_studio.core.mcap.mcap_dataset import McapDataset

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


@dataclass
class _LabelingContext:
    dataset: McapDataset
    topic: str
    suffix: str
    annotation_source: str
    by_uri: dict[str, _IndexedSequence]
    by_file_name: dict[str, list[_IndexedSequence]]
    labeled_sequence_ids: set[UUID]


def add_labels_from_folder(
    dataset: McapDataset,
    path: PathLike,
    topic: str,
    suffix: str = annotation_mcap.DEFAULT_ANNOTATION_MCAP_SUFFIX,
    annotation_source: str = add_labels.DEFAULT_ANNOTATION_SOURCE,
) -> None:
    """Store cuboids from annotation MCAPs in a folder on indexed sequences.

    A file that cannot be used is skipped and the reason is logged. The reasons are
    a missing or ambiguous recording, a file that is not a readable MCAP, a missing
    topic, and labels that do not join the ticks.
    """
    by_uri, by_file_name = recording_index(
        session=dataset.group_dataset.session, dataset_id=dataset.dataset_id
    )
    context = _LabelingContext(
        dataset=dataset,
        topic=topic,
        suffix=suffix,
        annotation_source=annotation_source,
        by_uri=by_uri,
        by_file_name=by_file_name,
        labeled_sequence_ids=_labeled_sequence_ids(
            dataset=dataset, annotation_source=annotation_source
        ),
    )
    if not by_uri:
        logger.warning("Dataset '%s' has no indexed recordings to add labels to.", dataset.name)
    annotation_uris = annotation_mcap_uris(path=str(path), suffix=suffix)
    if not annotation_uris:
        logger.warning(
            "No annotation MCAPs named '<recording>%s.mcap' found under '%s'.", suffix, path
        )
    report = FileOutcomeReport()
    for annotation_uri in annotation_uris:
        with report.track(annotation_uri):
            _add_labels_from_file(context=context, annotation_uri=annotation_uri)
    report.log_summary()


def _labeled_sequence_ids(dataset: McapDataset, annotation_source: str) -> set[UUID]:
    """Return sequences that already store this annotation source."""
    session = dataset.group_dataset.session
    collection_id = collection_resolver.get_by_name(
        session=session,
        name=annotation_source,
        parent_collection_id=dataset.group_dataset.collection_id,
    )
    if collection_id is None:
        return set()
    return annotation_collection_coverage_resolver.sequence_sample_ids(
        session=session, annotation_collection_id=collection_id
    )


def _add_labels_from_file(context: _LabelingContext, annotation_uri: str) -> None:
    """Persist cuboids from one annotation MCAP onto the sequence it names."""
    sequence_ref = match_sequence(
        annotation_uri=annotation_uri,
        suffix=context.suffix,
        by_uri=context.by_uri,
        by_file_name=context.by_file_name,
    )
    if sequence_ref.sample_id in context.labeled_sequence_ids:
        logger.info(
            "Skipping '%s': the sequence already has annotation source '%s'.",
            annotation_uri,
            context.annotation_source,
        )
        raise AlreadyPresentInputFileError()
    sequence = McapSequence(
        session=context.dataset.group_dataset.session,
        sample_id=sequence_ref.sample_id,
        recording_id=sequence_ref.recording_id,
    )
    try:
        messages = add_labels.read_scene_updates(
            annotation_mcap_uri=annotation_uri, topic=context.topic
        )
        add_labels.write_sequence_labels(
            dataset=context.dataset,
            sequence=sequence,
            annotation_mcap_uri=annotation_uri,
            messages=messages,
            annotation_source=context.annotation_source,
        )
    except FileNotFoundError as error:
        logger.error("Cannot add annotations from '%s': the file does not exist.", annotation_uri)
        raise MissingInputFileError() from error
    except (McapAccessError, McapError, OSError, ValueError) as error:
        # The report only counts the failure, so the reason is logged here.
        logger.error("Cannot add annotations from '%s': %s", annotation_uri, error)
        raise BrokenInputFileError() from error
    context.labeled_sequence_ids.add(sequence_ref.sample_id)
