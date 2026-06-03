"""Get annotation labels by IDs functionality."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio import db_array
from lightly_studio.models.annotation_label import AnnotationLabelTable


def get_by_ids(session: Session, ids: Sequence[UUID]) -> list[AnnotationLabelTable]:
    """Retrieve annotation labels by their IDs.

    Output order matches the input order.
    """
    ids_list = list(ids)
    if not ids_list:
        return []

    results = session.exec(
        select(AnnotationLabelTable).where(
            db_array.in_array(
                column=col(AnnotationLabelTable.annotation_label_id),
                values=ids_list,
            )
        )
    ).all()
    # Return labels in the same order as the input ids.
    label_map = {label.annotation_label_id: label for label in results}
    return [label_map[id_] for id_ in ids_list if id_ in label_map]
