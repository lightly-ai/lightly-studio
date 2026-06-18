"""Tests for the db_insert module."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import literal
from sqlmodel import Session, col, select

from lightly_studio.database import db_insert
from lightly_studio.models.sample import SampleTable, SampleTagLinkTable
from tests.helpers_resolvers import (
    ImageStub,
    create_collection,
    create_images,
    create_tag,
)


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
    samples = create_images(
        db_session=db_session,
        collection_id=collection_id,
        images=[ImageStub(path="/p/0.png"), ImageStub(path="/p/1.png")],
    )
    rows = [{"sample_id": sample.sample_id, "tag_id": tag.tag_id} for sample in samples]

    db_insert.insert_ignoring_conflicts(session=db_session, table=SampleTagLinkTable, rows=rows)
    db_session.commit()

    expected = {sample.sample_id for sample in samples}
    assert _linked_sample_ids(session=db_session, tag_id=tag.tag_id) == expected


def test_insert_ignoring_conflicts__skips_conflicting_rows(db_session: Session) -> None:
    """Re-inserting existing rows is ignored (no error); only genuinely new rows are added."""
    collection_id = create_collection(session=db_session).collection_id
    tag = create_tag(session=db_session, collection_id=collection_id)
    samples = create_images(
        db_session=db_session,
        collection_id=collection_id,
        images=[ImageStub(path=f"/p/{i}.png") for i in range(4)],
    )

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


def test_insert_from_select_ignoring_conflicts__inserts_rows(db_session: Session) -> None:
    """A server-side INSERT … SELECT links every sample the query returns."""
    collection_id = create_collection(session=db_session).collection_id
    tag = create_tag(session=db_session, collection_id=collection_id)
    samples = create_images(
        db_session=db_session,
        collection_id=collection_id,
        images=[ImageStub(path="/p/0.png"), ImageStub(path="/p/1.png")],
    )

    select_stmt = select(SampleTable.sample_id, literal(tag.tag_id)).where(
        col(SampleTable.collection_id) == collection_id
    )
    db_insert.insert_from_select_ignoring_conflicts(
        session=db_session,
        table=SampleTagLinkTable,
        columns=["sample_id", "tag_id"],
        select_stmt=select_stmt,
    )
    db_session.commit()

    expected = {sample.sample_id for sample in samples}
    assert _linked_sample_ids(session=db_session, tag_id=tag.tag_id) == expected


def test_insert_from_select_ignoring_conflicts__skips_conflicting_rows(db_session: Session) -> None:
    """Re-running the same INSERT … SELECT is ignored: no error and no duplicate links."""
    collection_id = create_collection(session=db_session).collection_id
    tag = create_tag(session=db_session, collection_id=collection_id)
    samples = create_images(
        db_session=db_session,
        collection_id=collection_id,
        images=[ImageStub(path="/p/0.png"), ImageStub(path="/p/1.png")],
    )

    select_stmt = select(SampleTable.sample_id, literal(tag.tag_id)).where(
        col(SampleTable.collection_id) == collection_id
    )
    for _ in range(2):
        db_insert.insert_from_select_ignoring_conflicts(
            session=db_session,
            table=SampleTagLinkTable,
            columns=["sample_id", "tag_id"],
            select_stmt=select_stmt,
        )
        db_session.commit()

    links = db_session.exec(
        select(SampleTagLinkTable).where(col(SampleTagLinkTable.tag_id) == tag.tag_id)
    ).all()
    # Every sample is linked exactly once despite running the insert twice.
    assert {link.sample_id for link in links} == {sample.sample_id for sample in samples}
    assert len(links) == len(samples)


def test_insert_from_select_ignoring_conflicts__empty_select_is_noop(db_session: Session) -> None:
    """A query matching no rows links nothing and does not error."""
    collection_id = create_collection(session=db_session).collection_id
    tag = create_tag(session=db_session, collection_id=collection_id)

    # No samples were created, so the select returns no rows.
    select_stmt = select(SampleTable.sample_id, literal(tag.tag_id)).where(
        col(SampleTable.collection_id) == collection_id
    )
    db_insert.insert_from_select_ignoring_conflicts(
        session=db_session,
        table=SampleTagLinkTable,
        columns=["sample_id", "tag_id"],
        select_stmt=select_stmt,
    )
    db_session.commit()

    assert _linked_sample_ids(session=db_session, tag_id=tag.tag_id) == set()
