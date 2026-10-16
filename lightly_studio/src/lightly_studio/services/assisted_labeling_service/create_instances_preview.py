"""Previews of all instances that match a text prompt or boxes."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.assisted_labeling.provider import SegmentationPrompt
from lightly_studio.models.assisted_labeling import (
    InstancesAnnotationRequest,
    InstancesAnnotationResponse,
)
from lightly_studio.services.assisted_labeling_service import (
    convert_prompts,
    get_active_provider,
    load_provider_image,
    segment_and_report,
    to_annotation_preview,
)


def create_instances_preview(
    session: Session, request: InstancesAnnotationRequest, user_email: str | None
) -> InstancesAnnotationResponse:
    """Returns the previews of all matching instances sorted by score. Saves nothing.

    The number of instances is limited by `request.max_instances` and by the provider.

    Args:
        session: Database session.
        request: The preview request.
        user_email: Email of the user who triggered the call, if known.

    Raises:
        NotFoundError: If the collection has no image with the sample ID.
        ProviderUnavailableError: If the active provider is not usable.
        ProviderError: If the provider fails.
    """
    provider = get_active_provider.get_usable_provider(session=session)
    image = load_provider_image.load_provider_image(
        session=session, collection_id=request.collection_id, sample_id=request.sample_id
    )
    max_masks = min(request.max_instances, provider.capabilities().max_instances)
    prompt = SegmentationPrompt(
        points=[],
        boxes=[
            convert_prompts.to_box_prompt(box=box, width=image.width, height=image.height)
            for box in request.boxes or []
        ],
        text=(request.prompt or "").strip() or None,
        max_masks=max_masks,
        output_type=request.output_type,
    )
    predictions, latency_ms = segment_and_report.segment_and_report(
        provider=provider,
        image=image,
        prompt=prompt,
        operation=segment_and_report.OPERATION_INSTANCES,
        collection_id=request.collection_id,
        user_email=user_email,
    )
    previews = to_annotation_preview.to_sorted_annotation_previews(
        predictions=predictions, width=image.width, height=image.height
    )
    return InstancesAnnotationResponse(predictions=previews[:max_masks], latency_ms=latency_ms)
