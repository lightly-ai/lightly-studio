"""ChatGPT image captioning provider."""

from __future__ import annotations

import base64
from typing import Any
from uuid import UUID

from sqlmodel import Session

from lightly_studio.auto_labeling.base_provider import (
    BaseAutoLabelingProvider,
    ProviderParameter,
    ProviderResult,
)
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers import tag_resolver


class ChatGPTCaptioningProvider(BaseAutoLabelingProvider):
    """Provider for generating captions using ChatGPT Vision API."""

    @property
    def provider_id(self) -> str:
        return "chatgpt_captioning"

    @property
    def name(self) -> str:
        return "ChatGPT Image Captioning"

    @property
    def description(self) -> str:
        return "Generate captions using GPT-4 Vision"

    @property
    def parameters(self) -> list[ProviderParameter]:
        return [
            ProviderParameter(
                name="api_key",
                type="string",
                description="OpenAI API key",
                required=True,
            ),
            ProviderParameter(
                name="prompt",
                type="string",
                description="Prompt for caption generation",
                default="Describe this image in one sentence.",
                required=True,
            ),
            ProviderParameter(
                name="tag_filter",
                type="tag_filter",
                description="Filter samples by tags",
                required=False,
            ),
            ProviderParameter(
                name="model",
                type="string",
                description="OpenAI model to use",
                default="gpt-4o",
                required=False,
            ),
            ProviderParameter(
                name="result_tag_name",
                type="string",
                description="Name of tag to add to processed samples",
                default="chatgpt-captioned",
                required=True,
            ),
        ]

    def execute(
        self,
        *,
        session: Session,
        collection_id: UUID,
        parameters: dict[str, Any],
    ) -> list[ProviderResult]:
        """Execute captioning on filtered samples."""
        api_key = parameters["api_key"]
        prompt = parameters.get("prompt", "Describe this image.")
        tag_filter = parameters.get("tag_filter")
        model = parameters.get("model", "gpt-4o")

        # Convert tag name to UUID if provided
        tag_ids = None
        if tag_filter:
            tag = tag_resolver.get_by_name(
                session=session,
                collection_id=collection_id,
                tag_name=tag_filter,
            )
            if tag:
                tag_ids = [tag.tag_id]
                print(f"[DEBUG] ChatGPT provider: Resolved tag '{tag_filter}' to UUID {tag.tag_id}")
            else:
                print(f"[DEBUG] ChatGPT provider: Tag '{tag_filter}' not found")

        # Get samples
        samples = self._get_samples_by_filter(session, collection_id, tag_ids)

        print(f"[DEBUG] ChatGPT provider: Found {len(samples)} samples to process")
        print(f"[DEBUG] tag_ids value: {tag_ids}, type: {type(tag_ids)}")

        results = []
        for sample in samples:
            try:
                caption = self._generate_caption(
                    session=session,
                    sample=sample,
                    api_key=api_key,
                    prompt=prompt,
                    model=model,
                )

                # Create caption using existing resolver
                from lightly_studio.models.caption import CaptionCreate
                from lightly_studio.resolvers import caption_resolver

                caption_resolver.create_many(
                    session=session,
                    parent_collection_id=collection_id,
                    captions=[
                        CaptionCreate(
                            parent_sample_id=sample.sample_id,
                            text=caption,
                        )
                    ],
                )

                results.append(
                    ProviderResult(
                        sample_id=sample.sample_id,
                        success=True,
                        data={"caption": caption},
                    )
                )
            except Exception as e:
                results.append(
                    ProviderResult(
                        sample_id=sample.sample_id,
                        success=False,
                        error_message=str(e),
                    )
                )

        return results

    def _generate_caption(
        self,
        session: Session,
        sample: SampleTable,
        api_key: str,
        prompt: str,
        model: str,
    ) -> str:
        """Generate caption for a single sample.

        Args:
            session: Database session.
            sample: Sample to generate caption for.
            api_key: OpenAI API key.
            prompt: Prompt to use for caption generation.
            model: Model to use.

        Returns:
            Generated caption text.
        """
        # Get image for this sample
        image = session.get(ImageTable, sample.sample_id)
        if not image:
            raise ValueError(f"No image found for sample {sample.sample_id}")

        # Get image path and encode
        image_path = image.file_path_abs
        with open(image_path, "rb") as f:
            image_base64 = base64.b64encode(f.read()).decode("utf-8")

        # Call OpenAI API
        response = self._make_api_request(
            url="https://api.openai.com/v1/chat/completions",
            method="POST",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json_data={
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}"
                                },
                            },
                        ],
                    }
                ],
                "max_tokens": 300,
            },
        )

        return response["choices"][0]["message"]["content"]
