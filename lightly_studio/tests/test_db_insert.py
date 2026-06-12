"""Tests for the db_insert module."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio import db_insert
from lightly_studio.models.sample import SampleTagLinkTable
from tests.helpers_resolvers import create_collection, create_image, create_tag


def _linked_sample_ids(session: Session, tag_id: UUID) -> set[UUID]:
    """Return the sample IDs linked to ``tag_id``."""
    links = session.exec(
        select(SampleTagLinkTable).where(col(SampleTagLinkTable.tag_id) == tag_id)
    ).all()
    return {link.sample_id for link in links if link.sample_id is not None}


def test_insert_ignoring_conflicts__inserts_rows(db_session: Session) -> None:
    """Rows are bulk-inserted and all become readable."""
    collection_id = create_collection(session=db_session).collection_id
    tag = create_tag(session=db_session, collection_id=collection_id)
    samples = [
        create_image(session=db_session, collection_id=collection_id, file_path_abs=f"/p/{i}.png")
        for i in range(3)
    ]
    rows = [{"sample_id": sample.sample_id, "tag_id": tag.tag_id} for sample in samples]

    db_insert.insert_ignoring_conflicts(session=db_session, table=SampleTagLinkTable, rows=rows)
    db_session.commit()

    expected = {sample.sample_id for sample in samples}
    assert _linked_sample_ids(session=db_session, tag_id=tag.tag_id) == expected


def test_insert_ignoring_conflicts__skips_conflicting_rows(db_session: Session) -> None:
    """Re-inserting existing rows is ignored (no error); only genuinely new rows are added."""
    collection_id = create_collection(session=db_session).collection_id
    tag = create_tag(session=db_session, collection_id=collection_id)
    samples = [
        create_image(session=db_session, collection_id=collection_id, file_path_abs=f"/p/{i}.png")
        for i in range(4)
    ]

    first = [{"sample_id": sample.sample_id, "tag_id": tag.tag_id} for sample in samples[:3]]
    db_insert.insert_ignoring_conflicts(session=db_session, table=SampleTagLinkTable, rows=first)
    db_session.commit()

    # Overlaps samples[1] and samples[2] (already linked) and adds samples[3].
    second = [{"sample_id": sample.sample_id, "tag_id": tag.tag_id} for sample in samples[1:]]
    db_insert.insert_ignoring_conflicts(session=db_session, table=SampleTagLinkTable, rows=second)
    db_session.commit()

    links = db_session.exec(
        select(SampleTagLinkTable).where(col(SampleTagLinkTable.tag_id) == tag.tag_id)
    ).all()
    # Every sample is linked exactly once; the overlapping rows neither raised nor duplicated.
    assert {link.sample_id for link in links} == {sample.sample_id for sample in samples}
    assert len(links) == len(samples)


def test_insert_ignoring_conflicts__empty_rows_is_noop(db_session: Session) -> None:
    """Empty input inserts nothing and does not error."""
    collection_id = create_collection(session=db_session).collection_id
    tag = create_tag(session=db_session, collection_id=collection_id)

    db_insert.insert_ignoring_conflicts(session=db_session, table=SampleTagLinkTable, rows=[])
    db_session.commit()

    assert _linked_sample_ids(session=db_session, tag_id=tag.tag_id) == set()
