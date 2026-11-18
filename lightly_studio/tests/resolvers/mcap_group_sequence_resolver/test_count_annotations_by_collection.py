"""Tests for count_annotations_by_collection in mcap_group_sequence_resolver."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.resolvers import mcap_group_sequence_resolver, tag_resolver
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter
from lightly_studio.resolvers.mcap_group_sequence_resolver.mcap_sequence_filter import (
    McapSequenceFilter,
)
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from lightly_studio.resolvers.video_resolver.count_video_frame_annotations_by_collection import (
    CountAnnotationsView,
)
from tests.helpers_resolvers import create_annotation, create_annotation_label, create_tag
from tests.resolvers.mcap_group_sequence_resolver import helpers

# The labels on each group of the two sequences that the count tests create. "car" is on both
# sequences, twice on sequence A. "person" is only on sequence B.
SEQUENCE_A_GROUP_LABELS = [["car"], ["car"]]
SEQUENCE_B_GROUP_LABELS = [["car", "person"]]


def test_count_annotations_by_collection__counts_distinct_sequences(db_session: Session) -> None:
    """A label on several groups of one sequence counts the sequence once."""
    sequence_a, _, _ = _create_two_annotated_sequences(session=db_session)

    result = mcap_group_sequence_resolver.count_annotations_by_collection(
        session=db_session, collection_id=sequence_a.sequence_collection.collection_id
    )

    assert result == [
        CountAnnotationsView(label_name="car", total_count=2, current_count=2),
        CountAnnotationsView(label_name="person", total_count=1, current_count=1),
    ]


def test_count_annotations_by_collection__current_count_respects_filter(
    db_session: Session,
) -> None:
    sequence_a, sequence_b, _ = _create_two_annotated_sequences(session=db_session)
    collection_id = sequence_a.sequence_collection.collection_id
    tag = create_tag(session=db_session, collection_id=collection_id)
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session, tag_id=tag.tag_id, sample_ids=[sequence_b.sample_id]
    )

    result = mcap_group_sequence_resolver.count_annotations_by_collection(
        session=db_session,
        collection_id=collection_id,
        filters=McapSequenceFilter(sample_filter=SampleFilter(tag_ids=[tag.tag_id])),
    )

    assert result == [
        CountAnnotationsView(label_name="car", total_count=2, current_count=1),
        CountAnnotationsView(label_name="person", total_count=1, current_count=1),
    ]


def test_count_annotations_by_collection__current_count_respects_label_filter(
    db_session: Session,
) -> None:
    sequence_a, _, labels = _create_two_annotated_sequences(session=db_session)

    result = mcap_group_sequence_resolver.count_annotations_by_collection(
        session=db_session,
        collection_id=sequence_a.sequence_collection.collection_id,
        filters=McapSequenceFilter(
            group_annotation_filter=AnnotationsFilter(annotation_label_ids=[labels["person"]])
        ),
    )

    assert result == [
        CountAnnotationsView(label_name="car", total_count=2, current_count=1),
        CountAnnotationsView(label_name="person", total_count=1, current_count=1),
    ]


def test_count_annotations_by_collection__sequence_without_annotations(
    db_session: Session,
) -> None:
    sequence = helpers.create_mcap_sequence(session=db_session)
    helpers.add_mcap_ticks_to_sequence(session=db_session, fixture=sequence, ticks=[(100, 100)])

    result = mcap_group_sequence_resolver.count_annotations_by_collection(
        session=db_session, collection_id=sequence.sequence_collection.collection_id
    )

    assert result == []


def test_count_annotations_by_collection__scoped_to_collection(db_session: Session) -> None:
    sequence = helpers.create_mcap_sequence(session=db_session)
    other_sequence = helpers.create_mcap_sequence(session=db_session)
    [other_group] = helpers.add_mcap_ticks_to_sequence(
        session=db_session, fixture=other_sequence, ticks=[(100, 100)]
    )
    car = create_annotation_label(
        session=db_session,
        root_collection_id=other_sequence.sequence_collection.collection_id,
        label_name="car",
    )
    create_annotation(
        session=db_session,
        collection_id=other_sequence.group_collection.collection_id,
        sample_id=other_group,
        annotation_label_id=car.annotation_label_id,
    )

    result = mcap_group_sequence_resolver.count_annotations_by_collection(
        session=db_session, collection_id=sequence.sequence_collection.collection_id
    )

    assert result == []


def test_count_annotations_by_collection__annotation_type(db_session: Session) -> None:
    sequence = helpers.create_mcap_sequence(session=db_session)
    [group] = helpers.add_mcap_ticks_to_sequence(
        session=db_session, fixture=sequence, ticks=[(100, 100)]
    )
    collection_id = sequence.sequence_collection.collection_id
    car = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="car"
    )
    night = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="night"
    )
    create_annotation(
        session=db_session,
        collection_id=sequence.group_collection.collection_id,
        sample_id=group,
        annotation_label_id=car.annotation_label_id,
        annotation_type=AnnotationType.OBJECT_DETECTION,
    )
    create_annotation(
        session=db_session,
        collection_id=sequence.group_collection.collection_id,
        sample_id=group,
        annotation_label_id=night.annotation_label_id,
        annotation_type=AnnotationType.CLASSIFICATION,
    )

    result = mcap_group_sequence_resolver.count_annotations_by_collection(
        session=db_session,
        collection_id=collection_id,
        annotation_type=AnnotationType.CLASSIFICATION,
    )

    assert result == [CountAnnotationsView(label_name="night", total_count=1, current_count=1)]


def _create_two_annotated_sequences(
    session: Session,
) -> tuple[helpers.McapSequenceFixture, helpers.McapSequenceFixture, dict[str, UUID]]:
    """Creates sequences A and B with SEQUENCE_A_GROUP_LABELS and SEQUENCE_B_GROUP_LABELS."""
    sequence_a = helpers.create_mcap_sequence(session=session)
    sequence_b = helpers.add_mcap_sequence(session=session, fixture=sequence_a)
    root_collection_id = sequence_a.sequence_collection.collection_id
    labels = {
        name: create_annotation_label(
            session=session, root_collection_id=root_collection_id, label_name=name
        ).annotation_label_id
        for name in ("car", "person")
    }
    for sequence, group_labels in (
        (sequence_a, SEQUENCE_A_GROUP_LABELS),
        (sequence_b, SEQUENCE_B_GROUP_LABELS),
    ):
        group_ids = helpers.add_mcap_ticks_to_sequence(
            session=session,
            fixture=sequence,
            ticks=[(100 * (index + 1), 100 * (index + 1)) for index in range(len(group_labels))],
        )
        for group_id, label_names in zip(group_ids, group_labels):
            for label_name in label_names:
                create_annotation(
                    session=session,
                    collection_id=sequence.group_collection.collection_id,
                    sample_id=group_id,
                    annotation_label_id=labels[label_name],
                )
    return sequence_a, sequence_b, labels
