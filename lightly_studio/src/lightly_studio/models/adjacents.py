"""Module containing the model for adjacent samples."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel

from lightly_studio.models.workflow import SampleWorkflowView


class AdjacentResultView(BaseModel):
    """Result of getting adjacent samples."""

    previous_sample_id: UUID | None
    sample_id: UUID
    next_sample_id: UUID | None
    current_sample_position: int
    total_count: int
    # The neighbours' labeling-workflow batch and state. Set only for image samples of a dataset
    # with a workflow project, and None for a neighbour in no batch.
    previous_workflow: SampleWorkflowView | None = None
    next_workflow: SampleWorkflowView | None = None
