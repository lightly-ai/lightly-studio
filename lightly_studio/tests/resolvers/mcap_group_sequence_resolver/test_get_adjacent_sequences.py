"""Tests for get_adjacent_sequences in mcap_group_sequence_resolver."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import numpy as np
import pytest
from pytest_mock import MockerFixture
from sqlmodel import Session, insert

from lightly_studio.models.collection import CollectionTable, SampleType
from lightly_studio.models.embedding_region import EmbeddingRegion, Point2D
from lightly_studio.models.mcap_group_sequence import McapGroupSequenceTable
from lightly_studio.models.recording import RecordingFormat
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.sample_embedding import SampleEmbeddingCreate
from lightly_studio.models.sequence import SequenceTable
from lightly_studio.models.workflow import SampleWorkflowView, WorkflowStatus
from lightly_studio.resolvers import (
    mcap_group_sequence_resolver,
    recording_resolver,
    sample_embedding_resolver,
    tag_resolver,
)
from lightly_studio.resolvers.mcap_group_sequence_resolver.mcap_sequence_filter import (
    McapSequenceFilter,
)
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from tests import helpers_workflow
from tests.helpers_resolvers import create_collection, create_embedding_model, create_tag

SEQ_ID_A = UUID("00000000-0000-0000-0000-000000000001")
SEQ_ID_B = UUID("00000000-0000-0000-0000-000000000002")
SEQ_ID_C = UUID("00000000-0000-0000-0000-000000000003")


def test_get_adjacent_sequences(db_session: Session) -> None:
    """Orders by created_at before sample_id."""
    seq_col = create_collection(session=db_session, sample_type=SampleType.SEQUENCE)
    _create_sequences(
        session=db_session,
        collection=seq_col,
        created_at_by_sample_id={
            SEQ_ID_C: datetime(2024, 1, 1, tzinfo=timezone.utc),
            SEQ_ID_A: datetime(2024, 1, 2, tzinfo=timezone.utc),
            SEQ_ID_B: datetime(2024, 1, 3, tzinfo=timezone.utc),
        },
    )

    result = mcap_group_sequence_resolver.get_adjacent_sequences(
        session=db_session,
        sample_id=SEQ_ID_A,
        collection_id=seq_col.collection_id,
    )

    assert result is not None
    assert result.previous_sample_id == SEQ_ID_C
    assert result.sample_id == SEQ_ID_A
    assert result.next_sample_id == SEQ_ID_B
    assert result.current_sample_position == 2
    assert result.total_count == 3


def test_get_adjacent_sequences__tied_created_at_ordered_by_sample_id(
    db_session: Session,
) -> None:
    seq_col = create_collection(session=db_session, sample_type=SampleType.SEQUENCE)
    fixed_time = datetime(2024, 1, 1, tzinfo=timezone.utc)
    _create_sequences(
        session=db_session,
        collection=seq_col,
        created_at_by_sample_id={
            SEQ_ID_C: fixed_time,
            SEQ_ID_B: fixed_time,
            SEQ_ID_A: fixed_time,
        },
    )

    result = mcap_group_sequence_resolver.get_adjacent_sequences(
        session=db_session,
        sample_id=SEQ_ID_B,
        collection_id=seq_col.collection_id,
    )

    assert result is not None
    assert result.previous_sample_id == SEQ_ID_A
    assert result.next_sample_id == SEQ_ID_C


def test_get_adjacent_sequences__ends_have_no_neighbour(db_session: Session) -> None:
    seq_col = create_collection(session=db_session, sample_type=SampleType.SEQUENCE)
    _create_sequences(
        session=db_session,
        collection=seq_col,
        created_at_by_sample_id={
            SEQ_ID_A: datetime(2024, 1, 1, tzinfo=timezone.utc),
            SEQ_ID_B: datetime(2024, 1, 2, tzinfo=timezone.utc),
        },
    )

    first = mcap_group_sequence_resolver.get_adjacent_sequences(
        session=db_session,
        sample_id=SEQ_ID_A,
        collection_id=seq_col.collection_id,
    )
    last = mcap_group_sequence_resolver.get_adjacent_sequences(
        session=db_session,
        sample_id=SEQ_ID_B,
        collection_id=seq_col.collection_id,
    )

    assert first is not None
    assert first.previous_sample_id is None
    assert first.next_sample_id == SEQ_ID_B
    assert last is not None
    assert last.previous_sample_id == SEQ_ID_A
    assert last.next_sample_id is None


def test_get_adjacent_sequences__scoped_to_collection(db_session: Session) -> None:
    seq_col_a = create_collection(session=db_session, sample_type=SampleType.SEQUENCE)
    seq_col_b = create_collection(session=db_session, sample_type=SampleType.SEQUENCE)
    _create_sequences(
        session=db_session,
        collection=seq_col_a,
        created_at_by_sample_id={
            SEQ_ID_A: datetime(2024, 1, 1, tzinfo=timezone.utc),
            SEQ_ID_C: datetime(2024, 1, 3, tzinfo=timezone.utc),
        },
    )
    _create_sequences(
        session=db_session,
        collection=seq_col_b,
        created_at_by_sample_id={SEQ_ID_B: datetime(2024, 1, 2, tzinfo=timezone.utc)},
    )

    result = mcap_group_sequence_resolver.get_adjacent_sequences(
        session=db_session,
        sample_id=SEQ_ID_A,
        collection_id=seq_col_a.collection_id,
    )
    other_collection_result = mcap_group_sequence_resolver.get_adjacent_sequences(
        session=db_session,
        sample_id=SEQ_ID_B,
        collection_id=seq_col_a.collection_id,
    )

    assert result is not None
    assert result.next_sample_id == SEQ_ID_C
    assert result.total_count == 2
    assert other_collection_result is None


def test_get_adjacent_sequences__filters(db_session: Session) -> None:
    """Only the tagged sequences are neighbours, so B is skipped."""
    seq_col = create_collection(session=db_session, sample_type=SampleType.SEQUENCE)
    _create_sequences(
        session=db_session,
        collection=seq_col,
        created_at_by_sample_id={
            SEQ_ID_A: datetime(2024, 1, 1, tzinfo=timezone.utc),
            SEQ_ID_B: datetime(2024, 1, 2, tzinfo=timezone.utc),
            SEQ_ID_C: datetime(2024, 1, 3, tzinfo=timezone.utc),
        },
    )
    tag = create_tag(session=db_session, collection_id=seq_col.collection_id)
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session, tag_id=tag.tag_id, sample_ids=[SEQ_ID_A, SEQ_ID_C]
    )

    result = mcap_group_sequence_resolver.get_adjacent_sequences(
        session=db_session,
        sample_id=SEQ_ID_A,
        collection_id=seq_col.collection_id,
        filters=McapSequenceFilter(sample_filter=SampleFilter(tag_ids=[tag.tag_id])),
    )

    assert result is not None
    assert result.previous_sample_id is None
    assert result.next_sample_id == SEQ_ID_C
    assert result.current_sample_position == 1
    assert result.total_count == 2


@pytest.mark.usefixtures("workflow_tables")
def test_get_adjacent_sequences__workflow_states(db_session: Session) -> None:
    """Only the accepted sequences are neighbours, so B is skipped."""
    seq_col = create_collection(session=db_session, sample_type=SampleType.SEQUENCE)
    _create_sequences(
        session=db_session,
        collection=seq_col,
        created_at_by_sample_id={
            SEQ_ID_A: datetime(2024, 1, 1, tzinfo=timezone.utc),
            SEQ_ID_B: datetime(2024, 1, 2, tzinfo=timezone.utc),
            SEQ_ID_C: datetime(2024, 1, 3, tzinfo=timezone.utc),
        },
    )
    project_id = helpers_workflow.create_project(
        session=db_session, dataset_id=seq_col.collection_id
    )
    helpers_workflow.add_batch_files(
        session=db_session,
        project_id=project_id,
        states={SEQ_ID_A: "accepted", SEQ_ID_B: "in_progress", SEQ_ID_C: "accepted"},
    )

    result = mcap_group_sequence_resolver.get_adjacent_sequences(
        session=db_session,
        sample_id=SEQ_ID_A,
        collection_id=seq_col.collection_id,
        filters=McapSequenceFilter(
            sample_filter=SampleFilter(workflow_states=[WorkflowStatus.ACCEPTED])
        ),
    )

    assert result is not None
    assert result.next_sample_id == SEQ_ID_C
    assert result.total_count == 2


@pytest.mark.usefixtures("workflow_tables")
def test_get_adjacent_sequences__neighbour_workflow(db_session: Session) -> None:
    """The neighbours carry their own batch and state, or none when they are not batched."""
    seq_col = create_collection(session=db_session, sample_type=SampleType.SEQUENCE)
    _create_sequences(
        session=db_session,
        collection=seq_col,
        created_at_by_sample_id={
            SEQ_ID_A: datetime(2024, 1, 1, tzinfo=timezone.utc),
            SEQ_ID_B: datetime(2024, 1, 2, tzinfo=timezone.utc),
            SEQ_ID_C: datetime(2024, 1, 3, tzinfo=timezone.utc),
        },
    )
    project_id = helpers_workflow.create_project(
        session=db_session, dataset_id=seq_col.collection_id
    )
    previous_batch_id = helpers_workflow.add_batch_files(
        session=db_session, project_id=project_id, states={SEQ_ID_A: "rework"}
    )
    # The anchor is in another batch: the neighbour keeps its own.
    helpers_workflow.add_batch_files(
        session=db_session, project_id=project_id, states={SEQ_ID_B: "in_progress"}
    )

    result = mcap_group_sequence_resolver.get_adjacent_sequences(
        session=db_session, sample_id=SEQ_ID_B, collection_id=seq_col.collection_id
    )

    assert result is not None
    assert result.previous_workflow == SampleWorkflowView(
        project_id=project_id, batch_id=previous_batch_id, state=WorkflowStatus.REWORK
    )
    assert result.next_workflow is None


def test_get_adjacent_sequences__no_neighbour_workflow_without_project(
    db_session: Session,
) -> None:
    """Without a workflow project, the neighbours have no batch or state."""
    seq_col = create_collection(session=db_session, sample_type=SampleType.SEQUENCE)
    _create_sequences(
        session=db_session,
        collection=seq_col,
        created_at_by_sample_id={
            SEQ_ID_A: datetime(2024, 1, 1, tzinfo=timezone.utc),
            SEQ_ID_B: datetime(2024, 1, 2, tzinfo=timezone.utc),
        },
    )

    result = mcap_group_sequence_resolver.get_adjacent_sequences(
        session=db_session, sample_id=SEQ_ID_A, collection_id=seq_col.collection_id
    )

    assert result is not None
    assert result.next_sample_id == SEQ_ID_B
    assert result.next_workflow is None


def test_get_adjacent_sequences__anchor_filtered_out(db_session: Session) -> None:
    seq_col = create_collection(session=db_session, sample_type=SampleType.SEQUENCE)
    _create_sequences(
        session=db_session,
        collection=seq_col,
        created_at_by_sample_id={
            SEQ_ID_A: datetime(2024, 1, 1, tzinfo=timezone.utc),
            SEQ_ID_B: datetime(2024, 1, 2, tzinfo=timezone.utc),
            SEQ_ID_C: datetime(2024, 1, 3, tzinfo=timezone.utc),
        },
    )

    result = mcap_group_sequence_resolver.get_adjacent_sequences(
        session=db_session,
        sample_id=SEQ_ID_B,
        collection_id=seq_col.collection_id,
        filters=McapSequenceFilter(sample_filter=SampleFilter(sample_ids=[SEQ_ID_A, SEQ_ID_C])),
    )

    assert result is None


def test_get_adjacent_sequences__resolves_embedding_region(
    db_session: Session, mocker: MockerFixture
) -> None:
    """The region is resolved to sample IDs before the filter is applied."""
    seq_col = create_collection(session=db_session, sample_type=SampleType.SEQUENCE)
    _create_sequences(
        session=db_session,
        collection=seq_col,
        created_at_by_sample_id={
            SEQ_ID_A: datetime(2024, 1, 1, tzinfo=timezone.utc),
            SEQ_ID_B: datetime(2024, 1, 2, tzinfo=timezone.utc),
            SEQ_ID_C: datetime(2024, 1, 3, tzinfo=timezone.utc),
        },
    )

    def _resolve_to_a_and_c(sequence_filter: McapSequenceFilter, **_: object) -> None:
        assert sequence_filter.sample_filter is not None
        sequence_filter.sample_filter.region_sample_ids = [SEQ_ID_A, SEQ_ID_C]

    mocker.patch.object(
        mcap_group_sequence_resolver,
        "resolve_embedding_region",
        side_effect=_resolve_to_a_and_c,
    )
    region = EmbeddingRegion(
        polygon=[Point2D(x=0.0, y=0.0), Point2D(x=1.0, y=0.0), Point2D(x=1.0, y=1.0)]
    )

    result = mcap_group_sequence_resolver.get_adjacent_sequences(
        session=db_session,
        sample_id=SEQ_ID_A,
        collection_id=seq_col.collection_id,
        filters=McapSequenceFilter(sample_filter=SampleFilter(embedding_region=region)),
    )

    assert result is not None
    assert result.next_sample_id == SEQ_ID_C
    assert result.total_count == 2


def test_get_adjacent_sequences__text_embedding(db_session: Session) -> None:
    """Orders by similarity. A sequence without an embedding is left out, as in the grid."""
    seq_col = create_collection(session=db_session, sample_type=SampleType.SEQUENCE)
    _create_sequences(
        session=db_session,
        collection=seq_col,
        created_at_by_sample_id={
            SEQ_ID_A: datetime(2024, 1, 1, tzinfo=timezone.utc),
            SEQ_ID_B: datetime(2024, 1, 2, tzinfo=timezone.utc),
            SEQ_ID_C: datetime(2024, 1, 3, tzinfo=timezone.utc),
        },
    )
    model = create_embedding_model(
        session=db_session,
        collection_id=seq_col.collection_id,
        embedding_dimension=3,
        set_as_default=True,
    )
    sample_embedding_resolver.create_many(
        session=db_session,
        sample_embeddings=[
            SampleEmbeddingCreate(
                sample_id=SEQ_ID_A,
                embedding_model_id=model.embedding_model_id,
                embedding=np.array([1.0, 0.0, 0.0], dtype=np.float32),
            ),
            SampleEmbeddingCreate(
                sample_id=SEQ_ID_B,
                embedding_model_id=model.embedding_model_id,
                embedding=np.array([0.0, 1.0, 0.0], dtype=np.float32),
            ),
        ],
    )

    result_b = mcap_group_sequence_resolver.get_adjacent_sequences(
        session=db_session,
        sample_id=SEQ_ID_B,
        collection_id=seq_col.collection_id,
        text_embedding=[0.0, 1.0, 0.0],
    )
    result_c = mcap_group_sequence_resolver.get_adjacent_sequences(
        session=db_session,
        sample_id=SEQ_ID_C,
        collection_id=seq_col.collection_id,
        text_embedding=[0.0, 1.0, 0.0],
    )

    assert result_b is not None
    assert result_b.previous_sample_id is None
    assert result_b.next_sample_id == SEQ_ID_A
    assert result_b.total_count == 2
    assert result_c is None


def _create_sequences(
    session: Session,
    collection: CollectionTable,
    created_at_by_sample_id: dict[UUID, datetime],
) -> None:
    """Creates MCAP sequences with fixed IDs and creation times in one recording."""
    recording_id = recording_resolver.create(
        session=session,
        dataset_id=collection.dataset_id,
        uri=f"/bags/{collection.collection_id}.mcap",
        format_=RecordingFormat.MCAP,
    )
    session.execute(
        insert(SampleTable).values(
            [
                {
                    "sample_id": sample_id,
                    "collection_id": collection.collection_id,
                    "created_at": created_at,
                    "updated_at": created_at,
                }
                for sample_id, created_at in created_at_by_sample_id.items()
            ]
        )
    )
    session.bulk_save_objects(
        [SequenceTable(sample_id=sample_id) for sample_id in created_at_by_sample_id]
    )
    session.bulk_save_objects(
        [
            McapGroupSequenceTable(sample_id=sample_id, recording_id=recording_id)
            for sample_id in created_at_by_sample_id
        ]
    )
    session.commit()
