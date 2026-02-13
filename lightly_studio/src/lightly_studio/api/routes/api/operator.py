"""API routes for operators."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from lightly_studio.api.routes.api.status import HTTP_STATUS_NOT_FOUND
from lightly_studio.db_manager import SessionDep
from lightly_studio.plugins.base_operator import BatchSampleOperator, OperatorResult
from lightly_studio.plugins.operator_registry import RegisteredOperatorMetadata, operator_registry
from lightly_studio.plugins.parameter import BaseParameter
from lightly_studio.resolvers import tag_resolver

logger = logging.getLogger(__name__)

operator_router = APIRouter(prefix="/operators", tags=["operators"])


class ExecuteOperatorRequest(BaseModel):
    """Request model for executing an operator."""

    parameters: dict[str, Any]


# --- Operator discovery ---


@operator_router.get("")
def get_operators() -> list[RegisteredOperatorMetadata]:
    """Get all registered operators (id, name, description, type)."""
    return operator_registry.get_all_metadata()


@operator_router.get("/{operator_id}/parameters")
def get_operator_parameters(operator_id: str) -> list[BaseParameter]:
    """Get the parameters for a registered operator."""
    operator = operator_registry.get_by_id(operator_id=operator_id)
    if operator is None:
        raise HTTPException(
            status_code=HTTP_STATUS_NOT_FOUND,
            detail=f"Operator '{operator_id}' not found",
        )
    return operator.parameters


# --- Operator execution ---


@operator_router.post(
    "/collections/{collection_id}/{operator_id}/execute",
    response_model=OperatorResult,
)
def execute_operator(
    operator_id: str,
    collection_id: UUID,
    request: ExecuteOperatorRequest,
    session: SessionDep,
) -> OperatorResult:
    """Execute an operator with the provided parameters.

    For batch operators, runs execute_batch() and tags successful samples.
    For simple operators, runs execute() directly.
    """
    operator = operator_registry.get_by_id(operator_id=operator_id)
    if operator is None:
        raise HTTPException(
            status_code=HTTP_STATUS_NOT_FOUND,
            detail=f"Operator '{operator_id}' not found",
        )

    if isinstance(operator, BatchSampleOperator):
        return _execute_batch_operator(
            operator=operator,
            session=session,
            collection_id=collection_id,
            parameters=request.parameters,
        )

    return operator.execute(
        session=session,
        collection_id=collection_id,
        parameters=request.parameters,
    )


def _execute_batch_operator(
    operator: BatchSampleOperator,
    session: SessionDep,
    collection_id: UUID,
    parameters: dict[str, Any],
) -> OperatorResult:
    """Run a batch operator, tag successful samples, return summary."""
    results = operator.execute_batch(
        session=session,
        collection_id=collection_id,
        parameters=parameters,
    )

    processed = sum(1 for r in results if r.success)
    errors = sum(1 for r in results if not r.success)

    # Create result tag and apply to successful samples
    result_tag_name = parameters.get(
        "result_tag_name", f"{operator.name}-processed"
    )
    result_tag = tag_resolver.get_or_create_sample_tag_by_name(
        session=session,
        collection_id=collection_id,
        tag_name=result_tag_name,
    )

    successful_sample_ids = [r.sample_id for r in results if r.success]
    if successful_sample_ids:
        tag_resolver.add_sample_ids_to_tag_id(
            session=session,
            tag_id=result_tag.tag_id,
            sample_ids=successful_sample_ids,
        )

    return OperatorResult(
        success=errors == 0,
        message=f"Processed {processed} samples, {errors} errors",
    )
