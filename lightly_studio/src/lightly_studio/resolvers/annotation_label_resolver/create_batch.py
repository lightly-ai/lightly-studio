"""Create multiple annotation labels functionality."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from lightly_studio.models.annotation_label import (
    AnnotationLabelCreate,
    AnnotationLabelTable,
)

from . import create, get_by_label_name


def create_batch(
    session: Session,
    dataset_id: UUID,
    label_names: Sequence[str],
) -> list[AnnotationLabelTable]:
    """Create multiple unique annotation labels, skipping existing names.

    Args:
        session: The database session.
        dataset_id: The dataset to create the annotation labels in.
        label_names: Annotation label names to create.

    Returns:
        The newly created annotation labels.
    """
    normalized_names = list(dict.fromkeys(name.strip() for name in label_names if name.strip()))
    created_labels: list[AnnotationLabelTable] = []
    for name in normalized_names:
        if get_by_label_name.get_by_label_name(
            session=session, dataset_id=dataset_id, label_name=name
        ):
            continue
        try:
            created_label = create.create(
                session=session,
                label=AnnotationLabelCreate(
                    dataset_id=dataset_id,
                    annotation_label_name=name,
                ),
            )
        except IntegrityError:
            session.rollback()
            continue
        created_labels.append(created_label)
    return created_labels
