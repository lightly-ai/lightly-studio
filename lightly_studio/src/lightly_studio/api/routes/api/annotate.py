"""Prototype auto-labeling and AI-assisted labeling endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from lightly_studio.database.db_manager import SessionDep
from lightly_studio.models.auto_labeling import (
    AnnotationDescriptorView,
    AutoLabelBatchRequest,
    AutoLabelBatchResponse,
    InstancesAnnotationRequest,
    InstancesAnnotationResponse,
    InteractiveAnnotationRequest,
    InteractiveAnnotationResponse,
)
from lightly_studio.services import auto_labeling
from lightly_studio.services.annotation_model_client import AnnotationModelClient

annotate_router = APIRouter(prefix="/annotate")


@annotate_router.get("/describe")
def describe_annotation_model() -> AnnotationDescriptorView:
    """Check the configured annotation model's readiness and capabilities."""
    client = AnnotationModelClient()
    return AnnotationDescriptorView(**client.describe().model_dump(), endpoint=client.endpoint)


@annotate_router.post("/batch")
def create_auto_label_batch(
    session: SessionDep, request: AutoLabelBatchRequest
) -> AutoLabelBatchResponse:
    """Run auto-labeling on a snapshot of the filtered images."""
    return auto_labeling.run_batch(session=session, request=request)


@annotate_router.post("/interactive")
def create_interactive_annotation_preview(
    session: SessionDep, request: InteractiveAnnotationRequest
) -> InteractiveAnnotationResponse:
    """Return a Smart select preview without persisting it."""
    return auto_labeling.infer_interactive(session=session, request=request)


@annotate_router.post("/instances")
def create_instances_annotation_preview(
    session: SessionDep, request: InstancesAnnotationRequest
) -> InstancesAnnotationResponse:
    """Return all matching instance masks without persisting them."""
    return auto_labeling.infer_instances(session=session, request=request)
