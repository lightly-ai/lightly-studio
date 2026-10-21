"""Single-object previews from point or box prompts."""

from __future__ import annotations

from lightly_studio.assisted_labeling.provider import (
    AssistedLabelingProvider,
    ProviderImage,
    SegmentationPrompt,
)
from lightly_studio.models.assisted_labeling import (
    InteractiveAnnotationRequest,
    InteractiveAnnotationResponse,
)
from lightly_studio.services.assisted_labeling_service import (
    convert_prompts,
    run_provider,
    to_annotation_preview,
)


def create_interactive_preview(
    provider: AssistedLabelingProvider,
    image: ProviderImage,
    request: InteractiveAnnotationRequest,
) -> InteractiveAnnotationResponse:
    """Returns the preview of the highest-scoring mask. Saves nothing.

    Raises:
        ProviderUnavailableError: If the provider is not configured.
        ProviderError: If the provider fails.
    """
    prompt = SegmentationPrompt(
        points=[
            convert_prompts.to_point_prompt(point=point, width=image.width, height=image.height)
            for point in request.points or []
        ],
        boxes=[
            convert_prompts.to_box_prompt(box=box, width=image.width, height=image.height)
            for box in request.boxes or []
        ],
        text=None,
        max_masks=1,
    )
    predictions = run_provider.segment(provider=provider, image=image, prompt=prompt)
    previews = to_annotation_preview.to_sorted_annotation_previews(
        predictions=predictions, width=image.width, height=image.height
    )
    return InteractiveAnnotationResponse(prediction=previews[0] if previews else None)
