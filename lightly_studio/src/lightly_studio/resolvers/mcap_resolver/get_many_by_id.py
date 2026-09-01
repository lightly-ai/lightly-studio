"""Implementation of get_many_by_id function for mcap locators."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.mcap import McapTable
from lightly_studio.utils import batching


def get_many_by_id(session: Session, sample_ids: list[UUID]) -> list[McapTable]:
    """Retrieve multiple mcap locator samples by their IDs.

    Main purpose: Return a batch of mcap locators for all the specified samples.
    Use case: When you have a list of samples and need to get information about
    mcap locators for all of them efficiently in a single query.

    Output order matches the input order.
    """
    results: list[McapTable] = []
    for batch in batching.batched(items=sample_ids):
        results.extend(
            session.exec(select(McapTable).where(col(McapTable.sample_id).in_(batch))).all()
        )
    # Return samples in the same order as the input IDs
    sample_map = {sample.sample_id: sample for sample in results}
    return [sample_map[id_] for id_ in sample_ids if id_ in sample_map]
