"""Operator plugin that creates a new dataset from a tag and/or a samples folder.

Triggered from the GUI on an existing dataset, this operator can:
- Copy the samples carrying a given tag into a new dataset (deep or samples-only).
- Load images from a filesystem path into the new dataset.
- Do both: split by tag, then top up the new dataset with images from disk.

If ``tag`` is empty, a fresh empty dataset is created and only the ``samples_path``
images are loaded into it.

All DB work uses only the session passed into ``execute()`` so the operator is safe
to run from a background worker thread. The high-level ``lightly_studio`` API
(``ImageDataset.create`` / ``add_images_from_path``) is avoided because it touches
the process-global persistent session, which is not thread-safe.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from lightly_studio.core.image.image_dataset import _generate_embeddings_image
from sqlmodel import Session

from lightly_studio.core.image import add_images
from lightly_studio.dataset import fsspec_lister
from lightly_studio.models.collection import CollectionCreate, CollectionTable, SampleType
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
        new_root: CollectionTable
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
            new_root, copied_count = result
        else:
            new_root = collection_resolver.create(
                session=session,
                collection=CollectionCreate(name=new_name, sample_type=SampleType.IMAGE),
            )

        added_count = 0
        if samples_path:
            image_paths = list(fsspec_lister.iter_files_from_path(path=samples_path))
            created_sample_ids = add_images.load_into_dataset_from_paths(
                session=session,
                root_collection_id=new_root.collection_id,
                image_paths=image_paths,
            )
            _generate_embeddings_image(
                session=session,
                sample_ids=created_sample_ids,
                collection_id=new_root.collection_id,)
            added_count = len(created_sample_ids)

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
    ) -> OperatorResult | tuple[CollectionTable, int]:
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
            new_root = dataset_resolver.copy_images_subset(
                session=session,
                dataset_id=source_collection.dataset_id,
                copy_name=new_name,
                sample_ids=sample_ids,
            )
        else:
            new_root = dataset_resolver.deep_copy_subset(
                session=session,
                dataset_id=source_collection.dataset_id,
                copy_name=new_name,
                sample_ids=sample_ids,
            )
        return new_root, len(sample_ids)
