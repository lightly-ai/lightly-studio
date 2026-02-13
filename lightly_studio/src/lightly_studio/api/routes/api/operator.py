"""API routes for operators."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from lightly_studio.api.routes.api.status import HTTP_STATUS_NOT_FOUND
from lightly_studio.db_manager import SessionDep
from lightly_studio.plugins.base_operator import OperatorResult
from lightly_studio.plugins.operator_registry import RegisteredOperatorMetadata, operator_registry
from lightly_studio.plugins.parameter import BaseParameter

operator_router = APIRouter(prefix="/operators", tags=["operators"])


class ExecuteOperatorRequest(BaseModel):
    """Request model for executing an operator."""

    parameters: dict[str, Any]


@operator_router.get("")
def get_operators() -> list[RegisteredOperatorMetadata]:
    """Get all registered operators (id, name)."""
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


@operator_router.post(
    "/collections/{collection_id}/{operator_id}/execute", response_model=OperatorResult
)
def execute_operator(
    operator_id: str,
    collection_id: UUID,
    request: ExecuteOperatorRequest,
    session: SessionDep,
) -> OperatorResult:
    """Execute an operator with the provided parameters.

    Args:
        operator_id: The ID of the operator to execute.
        collection_id: The ID of the collection to operate on.
        request: The execution request containing parameters.
        session: Database session.

    Returns:
        The execution result.
    """
    # Get the operator
    operator = operator_registry.get_by_id(operator_id=operator_id)
    if operator is None:
        raise HTTPException(
            status_code=HTTP_STATUS_NOT_FOUND,
            detail=f"Operator '{operator_id}' not found",
        )

    # Execute the operator
    return operator.execute(
        session=session,
        collection_id=collection_id,
        parameters=request.parameters,
    )
