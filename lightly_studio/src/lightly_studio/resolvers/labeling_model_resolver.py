"""Resolvers for the labeling model servers that a dataset saves."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.labeling_model import LabelingModelCreate, LabelingModelTable


def set_remote(session: Session, labeling_model: LabelingModelCreate) -> LabelingModelTable:
    """Save the server of a labeling model in its dataset.

    A model with the same ID in the dataset gets the new URL and API key.

    Args:
        session: The database session.
        labeling_model: The dataset, the model ID, the URL and the API key to save.

    Returns:
        The saved labeling model.
    """
    db_labeling_model = get_by_model_id(
        session=session, dataset_id=labeling_model.dataset_id, model_id=labeling_model.model_id
    )
    if db_labeling_model is None:
        db_labeling_model = LabelingModelTable.model_validate(labeling_model)
    else:
        db_labeling_model.url = labeling_model.url
        db_labeling_model.api_key = labeling_model.api_key
    session.add(db_labeling_model)
    session.commit()
    session.refresh(db_labeling_model)
    return db_labeling_model


def get_by_model_id(session: Session, dataset_id: UUID, model_id: str) -> LabelingModelTable | None:
    """Retrieve the labeling model of a dataset with the model ID."""
    query = select(LabelingModelTable).where(
        LabelingModelTable.dataset_id == dataset_id, LabelingModelTable.model_id == model_id
    )
    return session.exec(query).one_or_none()


def get_all_by_dataset_id(session: Session, dataset_id: UUID) -> list[LabelingModelTable]:
    """Retrieve all labeling models of a dataset, ordered by model ID."""
    query = (
        select(LabelingModelTable)
        .where(LabelingModelTable.dataset_id == dataset_id)
        .order_by(col(LabelingModelTable.model_id))
    )
    return list(session.exec(query).all())
