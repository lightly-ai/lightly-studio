"""API routes for evaluation runs.

Each route handler is defined in its own module with its own ``APIRouter``.
This barrel aggregates them into a single ``evaluation_router`` mounted by the
application.
"""

from __future__ import annotations

from fastapi import APIRouter

from lightly_studio.api.routes.api.evaluation.create_run import create_run_router
from lightly_studio.api.routes.api.evaluation.get_confusion_matrix import (
    get_confusion_matrix_router,
)
from lightly_studio.api.routes.api.evaluation.get_runs import get_runs_router
from lightly_studio.api.routes.api.evaluation.get_sample_metrics_info import (
    get_sample_metrics_info_router,
)

evaluation_router = APIRouter(prefix="/datasets/{dataset_id}", tags=["evaluation"])
evaluation_router.include_router(create_run_router)
evaluation_router.include_router(get_runs_router)
evaluation_router.include_router(get_sample_metrics_info_router)
evaluation_router.include_router(get_confusion_matrix_router)

__all__ = ["evaluation_router"]
