"""Operator plugin that creates a new dataset from a tag and/or a samples folder.

Triggered from the GUI on an existing dataset, this operator can:
- Copy the samples carrying a given tag into a new dataset (deep or samples-only).
- Load images from a filesystem path into the new dataset.
- Do both: split by tag, then top up the new dataset with images from disk.

If ``tag`` is empty, a fresh empty dataset is created and only the ``samples_path``
images are loaded into it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlmodel import Session

import lightly_studio as ls
from lightly_studio.plugins.base_operator import BaseOperator, OperatorResult
from lightly_studio.plugins.operator_context import ExecutionContext, OperatorScope
from lightly_studio.plugins.parameter import BaseParameter, BoolParameter, StringParameter
from lightly_studio.resolvers import (
    collection_resolver,
    dataset_resolver,
    sample_resolver,
    tag_resolver,
)
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter


@dataclass
class SplitByTagOperator(BaseOperator):
    """Create a new dataset from a tag selection and/or a folder of images."""

    name: str = "Split dataset by tag"
    description: str = (
        "Create a new dataset from the current one. Optionally restrict to samples "
        "carrying a tag, and optionally add images from a folder."
    )

    @property
    def parameters(self) -> list[BaseParameter]:
        return [
            StringParameter(
                name="new_dataset_name",
                required=True,
                description="Name of the new dataset to create.",
            ),
            StringParameter(
                name="tag",
                required=False,
                default="",
                description=(
                    "Optional. Name of the tag to filter samples by. Leave empty to "
                    "skip copying and only load images from 'samples_path'."
                ),
            ),
            StringParameter(
                name="samples_path",
                required=False,
                default="",
                description=(
                    "Optional. Filesystem path to a folder of images to add to the "
                    "new dataset."
                ),
            ),
            BoolParameter(
                name="samples_only",
                required=False,
                default=False,
                description=(
                    "If true, copy only the image samples (no annotations, tags, "
                    "embeddings, metadata, captions, or evaluation runs). Only "
                    "applies when 'tag' is provided."
                ),
            ),
        ]

    @property
    def supported_scopes(self) -> list[OperatorScope]:
        return [OperatorScope.ROOT, OperatorScope.IMAGE]

    def execute(
        self,
        *,
        session: Session,
        context: ExecutionContext,
        parameters: dict[str, Any],
    ) -> OperatorResult:
        new_name = str(parameters["new_dataset_name"]).strip()
        tag_name = str(parameters.get("tag") or "").strip()
        samples_path = str(parameters.get("samples_path") or "").strip()
        samples_only = bool(parameters.get("samples_only", False))

        if not new_name:
            return OperatorResult(success=False, message="'new_dataset_name' is required.")
        if not tag_name and not samples_path:
            return OperatorResult(
                success=False,
                message="Provide a 'tag', a 'samples_path', or both.",
            )

        copied_count = 0
        if tag_name:
            result = self._copy_tagged_subset(
                session=session,
                context=context,
                new_name=new_name,
                tag_name=tag_name,
                samples_only=samples_only,
            )
            if isinstance(result, OperatorResult):
                return result
            copied_count = result
        else:
            # No tag: create a fresh empty dataset to be filled from the folder.
            ls.ImageDataset.create(name=new_name)

        added_count = 0
        if samples_path:
            new_dataset = ls.ImageDataset.load(name=new_name)
            samples_before = len(list(new_dataset))
            new_dataset.add_images_from_path(path=samples_path)
            added_count = len(list(new_dataset)) - samples_before

        mode_suffix = " (samples-only)" if tag_name and samples_only else ""
        path_suffix = f", added {added_count} from '{samples_path}'" if samples_path else ""
        return OperatorResult(
            success=True,
            message=(
                f"Created dataset '{new_name}': copied {copied_count} samples"
                f"{mode_suffix}{path_suffix}."
            ),
        )

    def _copy_tagged_subset(
        self,
        *,
        session: Session,
        context: ExecutionContext,
        new_name: str,
        tag_name: str,
        samples_only: bool,
    ) -> OperatorResult | int:
        """Run the tag-driven copy. Returns the number of copied samples or an error."""
        source_collection = collection_resolver.get_by_id(
            session=session, collection_id=context.collection_id
        )
        if source_collection is None:
            return OperatorResult(
                success=False, message=f"Collection {context.collection_id} not found."
            )

        tag = tag_resolver.get_by_name(
            session=session, tag_name=tag_name, collection_id=context.collection_id
        )
        if tag is None:
            return OperatorResult(
                success=False, message=f"Tag '{tag_name}' not found in this dataset."
            )

        tagged = sample_resolver.get_filtered_samples(
            session=session,
            collection_id=context.collection_id,
            filters=SampleFilter(tag_ids=[tag.tag_id]),
        )
        if tagged.total_count == 0:
            return OperatorResult(success=False, message=f"No samples carry tag '{tag_name}'.")

        sample_ids = [s.sample_id for s in tagged.samples]
        if samples_only:
            dataset_resolver.copy_images_subset(
                session=session,
                dataset_id=source_collection.dataset_id,
                copy_name=new_name,
                sample_ids=sample_ids,
            )
        else:
            dataset_resolver.deep_copy_subset(
                session=session,
                dataset_id=source_collection.dataset_id,
                copy_name=new_name,
                sample_ids=sample_ids,
            )
        return len(sample_ids)
