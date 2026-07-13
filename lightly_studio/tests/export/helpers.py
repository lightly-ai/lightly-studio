"""Shared helpers for export tests."""

from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from sqlmodel import Session

from lightly_studio.core.sample import Sample
from lightly_studio.export import image_dataset_export
from lightly_studio.export.dataset_export import DatasetExport


def build_dataset_export(
    *,
    session: Session,
    dataset_id: UUID,
    samples: Iterable[Sample],
) -> DatasetExport:
    """Builds a `DatasetExport` that maps image samples to labelformat images."""
    return DatasetExport(
        session=session,
        dataset_id=dataset_id,
        samples=samples,
        sample_to_image=image_dataset_export.image_sample_to_image,
    )
