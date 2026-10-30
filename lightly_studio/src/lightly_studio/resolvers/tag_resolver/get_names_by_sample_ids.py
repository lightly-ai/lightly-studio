"""Implementation of get_names_by_sample_ids function for tags."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.database import db_array
from lightly_studio.models.sample import SampleTagLinkTable
from lightly_studio.models.tag import TagTable


def get_names_by_sample_ids(session: Session, sample_ids: Sequence[UUID]) -> dict[UUID, list[str]]:
    """Return ``{sample_id: [name, ...]}`` for the requested samples.

    The names of a sample are sorted. A sample without tags is not in the result.
    """
    if not sample_ids:
        return {}
    stmt = (
        select(SampleTagLinkTable.sample_id, TagTable.name)
        .join(TagTable, col(TagTable.tag_id) == col(SampleTagLinkTable.tag_id))
        .where(db_array.in_array(column=col(SampleTagLinkTable.sample_id), values=sample_ids))
        .order_by(col(TagTable.name))
    )
    result: dict[UUID, list[str]] = {}
    for sample_id, name in session.exec(stmt).all():
        assert sample_id is not None
        result.setdefault(sample_id, []).append(name)
    return result
