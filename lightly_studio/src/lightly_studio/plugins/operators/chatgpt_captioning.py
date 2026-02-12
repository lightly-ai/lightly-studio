"""ChatGPT image captioning operator."""

from __future__ import annotations

import base64
from typing import Any
from uuid import UUID

from sqlmodel import Session

from lightly_studio.plugins.base_operator import (
    BatchSampleOperator,
    SampleResult,
)
from lightly_studio.plugins.parameter import (
    BaseParameter,
    StringParameter,
    TagFilterParameter,
)
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers import tag_resolver


class ChatGPTCaptioningOperator(BatchSampleOperator):
    """Operator for generating captions using ChatGPT Vision API."""

    @property
    def name(self) -> str:
        return "ChatGPT Image Captioning"

    @property
    def description(self) -> str:
        return "Generate captions using GPT-4 Vision"

    @property
    def parameters(self) -> list[BaseParameter]:
        return [
            StringParameter(
                name="api_key",
                description="OpenAI API key",
                required=True,
            ),
            StringParameter(
                name="prompt",
                description="Prompt for caption generation",
                default="Describe this image in one sentence.",
                required=True,
            ),
            TagFilterParameter(
                name="tag_filter",
                description="Filter samples by tags",
                required=False,
            ),
            StringParameter(
                name="model",
                description="OpenAI model to use",
                default="gpt-4o",
                required=False,
            ),
            StringParameter(
                name="result_tag_name",
                description="Name of tag to add to processed samples",
                default="chatgpt-captioned",
                required=True,
            ),
        ]

    def execute_batch(
        self,
        *,
        session: Session,
        collection_id: UUID,
        parameters: dict[str, Any],
    ) -> list[SampleResult]:
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

        # Get samples
        samples = self._get_samples_by_filter(session, collection_id, tag_ids)

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
                    SampleResult(
                        sample_id=sample.sample_id,
                        success=True,
                        data={"caption": caption},
                    )
                )
            except Exception as e:
                results.append(
                    SampleResult(
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
        """Generate caption for a single sample."""
        image = session.get(ImageTable, sample.sample_id)
        if not image:
            raise ValueError(f"No image found for sample {sample.sample_id}")

        image_path = image.file_path_abs
        with open(image_path, "rb") as f:
            image_base64 = base64.b64encode(f.read()).decode("utf-8")

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
