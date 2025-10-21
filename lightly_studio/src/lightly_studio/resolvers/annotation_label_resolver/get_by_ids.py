"""Get annotation labels by IDs functionality."""

from __future__ import annotations

from typing import Sequence
from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.annotation_label import AnnotationLabelTable


def get_by_ids(session: Session, ids: Sequence[UUID]) -> list[AnnotationLabelTable]:
    """Retrieve annotation labels by their IDs.

    Output order matches the input order.
    """
    results = session.exec(
        select(AnnotationLabelTable).where(
            col(AnnotationLabelTable.annotation_label_id).in_(list(ids))
        )
    ).all()
    # Return labels in the same order as the input ids.
    label_map = {label.annotation_label_id: label for label in results}
    return [label_map[id_] for id_ in ids if id_ in label_map]
