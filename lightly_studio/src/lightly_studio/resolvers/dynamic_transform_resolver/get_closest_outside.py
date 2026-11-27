"""Read the dynamic transform edges closest to a range of capture times."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import ColumnElement, UnaryExpression, func
from sqlalchemy.orm import aliased
from sqlmodel import Session, col, select

from lightly_studio.models.dynamic_transform import DynamicTransformTable


def get_closest_outside(
    session: Session,
    recording_id: UUID,
    start_ns: int,
    end_ns: int,
) -> list[DynamicTransformTable]:
    """Return the closest edges before and after a range of capture times, per child frame.

    For each child frame, return its last edge before ``start_ns`` and its first edge
    after ``end_ns``, if they exist.
    """
    timestamp = col(DynamicTransformTable.timestamp_ns)
    return [
        *_first_per_child(
            session=session,
            recording_id=recording_id,
            condition=timestamp < start_ns,
            order=timestamp.desc(),
        ),
        *_first_per_child(
            session=session,
            recording_id=recording_id,
            condition=timestamp > end_ns,
            order=timestamp.asc(),
        ),
    ]


def _first_per_child(
    session: Session,
    recording_id: UUID,
    condition: ColumnElement[bool],
    order: UnaryExpression[int],
) -> list[DynamicTransformTable]:
    """Return the first edge of each child frame that matches `condition`, in `order`."""
    ranked = (
        select(
            DynamicTransformTable,
            func.row_number()
            .over(partition_by=col(DynamicTransformTable.child), order_by=order)
            .label("rank"),
        )
        .where(col(DynamicTransformTable.recording_id) == recording_id, condition)
        .subquery()
    )
    ranked_transform = aliased(DynamicTransformTable, ranked)
    return list(session.exec(select(ranked_transform).where(ranked.c.rank == 1)).all())
