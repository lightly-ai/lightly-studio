"""Implementation of get_many_by_id for sample resolver."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.sample import SampleTable


def get_many_by_id(session: Session, sample_ids: list[UUID]) -> list[SampleTable]:
    """Retrieve multiple samples by their IDs.

    Output order matches the input order.
    """
    results = session.exec(
        select(SampleTable).where(col(SampleTable.sample_id).in_(sample_ids))
    ).all()
    # Return samples in the same order as the input IDs
    sample_map = {sample.sample_id: sample for sample in results}
    return [sample_map[id_] for id_ in sample_ids if id_ in sample_map]
