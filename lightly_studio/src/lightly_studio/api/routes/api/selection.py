"""This module contains the API routes for managing selections."""

from __future__ import annotations

from typing import Union

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing_extensions import Annotated

from lightly_studio.api.routes.api.dataset import get_and_validate_dataset_id
from lightly_studio.db_manager import SessionDep
from lightly_studio.models.dataset import DatasetTable
from lightly_studio.resolvers import sample_resolver
from lightly_studio.selection.select_via_db import select_via_database
from lightly_studio.selection.selection_config import (
    EmbeddingDiversityStrategy,
    MetadataWeightingStrategy,
    SelectionConfig,
)

selection_router = APIRouter()

Strategy = Annotated[
    Union[EmbeddingDiversityStrategy, MetadataWeightingStrategy],
    Field(discriminator="strategy_name"),
]


class SelectionRequest(BaseModel):
    """Request model for selection."""

    n_samples_to_select: int = Field(gt=0, description="Number of samples to select")
    selection_result_tag_name: str = Field(min_length=1, description="Name for the result tag")
    strategies: list[Strategy]


@selection_router.post(
    "/datasets/{dataset_id}/selection",
    status_code=204,
    response_model=None,
)
def create_combination_selection(
    session: SessionDep,
    dataset: Annotated[
        DatasetTable,
        Depends(get_and_validate_dataset_id),
    ],
    request: SelectionRequest,
) -> None:
    """Create a combination selection on the dataset.

    This endpoint performs combination selection using embeddings and metadata.
    The selected samples are tagged with the specified tag name.

    Args:
        session: Database session dependency.
        dataset: Dataset to perform selection on.
        request: Selection parameters including sample count and tag name.

    Returns:
        None (204 No Content on success).

    Raises:
        HTTPException: 400 if selection fails due to invalid parameters or other errors.
    """
    # Get all samples in dataset as input for selection.
    all_samples_result = sample_resolver.get_all_by_dataset_id(
        session=session, dataset_id=dataset.dataset_id
    )
    input_sample_ids = [sample.sample_id for sample in all_samples_result.samples]
    # Validate we have enough samples to select from.
    if len(input_sample_ids) < request.n_samples_to_select:
        raise HTTPException(
            status_code=400,
            detail=f"Dataset has only {len(input_sample_ids)} samples, "
            f"cannot select {request.n_samples_to_select}",
        )
    # Create SelectionConfig with diversity strategy.
    config = SelectionConfig(
        dataset_id=dataset.dataset_id,
        n_samples_to_select=request.n_samples_to_select,
        selection_result_tag_name=request.selection_result_tag_name,
        strategies=request.strategies,
    )
    # Perform selection via database.
    select_via_database(session=session, config=config, input_sample_ids=input_sample_ids)
