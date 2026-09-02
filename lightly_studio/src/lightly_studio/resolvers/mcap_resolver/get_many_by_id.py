"""Implementation of get_many_by_id function for mcap locators."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.mcap import McapTable
from lightly_studio.utils import batching


def get_many_by_id(session: Session, sample_ids: list[UUID]) -> list[McapTable]:
    """Retrieve multiple mcap locator samples by their IDs.

    Output order matches the input order. Sample IDs with no matching MCAP
    record are silently omitted from the result.
    """
    results: list[McapTable] = []
    for batch in batching.batched(items=sample_ids):
        results.extend(
            session.exec(select(McapTable).where(col(McapTable.sample_id).in_(batch))).all()
        )
    sample_map = {sample.sample_id: sample for sample in results}
    # Return samples in the same order as the input IDs, dropping IDs with no match.
    return [sample_map[id_] for id_ in sample_ids if id_ in sample_map]
