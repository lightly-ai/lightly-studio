"""Single-object previews from point or box prompts."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.assisted_labeling.provider import SegmentationPrompt
from lightly_studio.models.assisted_labeling import (
    InteractiveAnnotationRequest,
    InteractiveAnnotationResponse,
)
from lightly_studio.services.assisted_labeling_service import (
    convert_prompts,
    get_active_provider,
    load_provider_image,
    segment_timed,
    to_annotation_preview,
)


def create_interactive_preview(
    session: Session, request: InteractiveAnnotationRequest
) -> InteractiveAnnotationResponse:
    """Returns the preview of the highest-scoring mask. Saves nothing.

    Raises:
        NotFoundError: If the collection has no image with the sample ID.
        ProviderUnavailableError: If the active provider is not usable.
        ProviderError: If the provider fails.
    """
    provider = get_active_provider.get_usable_provider(session=session)
    image = load_provider_image.load_provider_image(
        session=session, collection_id=request.collection_id, sample_id=request.sample_id
    )
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
        output_type=request.output_type,
    )
    predictions, latency_ms = segment_timed.segment_timed(
        provider=provider, image=image, prompt=prompt
    )
    previews = to_annotation_preview.to_sorted_annotation_previews(
        predictions=predictions, width=image.width, height=image.height
    )
    return InteractiveAnnotationResponse(
        prediction=previews[0] if previews else None, latency_ms=latency_ms
    )
