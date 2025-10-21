"""This module defines the data model for the classifier."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class EmbeddingClassifier(BaseModel):
    """Base class for the Classifier model."""

    """The name of the classifier."""
    classifier_name: str

    """The ID of the classifier."""
    classifier_id: UUID

    """List of classes supported by the classifier."""
    class_list: list[str]
