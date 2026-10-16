"""Previews of all instances that match a text prompt or boxes."""

from __future__ import annotations

from lightly_studio.assisted_labeling.provider import (
    AssistedLabelingProvider,
    ProviderImage,
    SegmentationPrompt,
)
from lightly_studio.models.assisted_labeling import (
    InstancesAnnotationRequest,
    InstancesAnnotationResponse,
)
from lightly_studio.services.assisted_labeling_service import (
    convert_prompts,
    run_provider,
    to_annotation_preview,
)


def create_instances_preview(
    provider: AssistedLabelingProvider,
    image: ProviderImage,
    request: InstancesAnnotationRequest,
) -> InstancesAnnotationResponse:
    """Returns the previews of all matching instances sorted by score. Saves nothing.

    The number of instances is limited by `request.max_instances`.

    Raises:
        ProviderUnavailableError: If the provider is not configured.
        ProviderError: If the provider fails.
    """
    prompt = SegmentationPrompt(
        points=[],
        boxes=[
            convert_prompts.to_box_prompt(box=box, width=image.width, height=image.height)
            for box in request.boxes or []
        ],
        text=(request.prompt or "").strip() or None,
        max_masks=request.max_instances,
    )
    predictions = run_provider.segment(provider=provider, image=image, prompt=prompt)
    previews = to_annotation_preview.to_sorted_annotation_previews(
        predictions=predictions, width=image.width, height=image.height
    )
    return InstancesAnnotationResponse(predictions=previews[: request.max_instances])
