"""Tests for count_by_status resolver."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.dataset import DatasetTable
from lightly_studio.models.image import ImageCreate
from lightly_studio.resolvers import image_resolver


def test_count_by_status(db_session: Session, dataset: DatasetTable) -> None:
    """Counts should reflect current image statuses."""
    # Create three images with default status READY.
    sample_ids = image_resolver.create_many(
        session=db_session,
        dataset_id=dataset.dataset_id,
        samples=[
            ImageCreate(
                file_path_abs=f"/path/to/img_{i}.jpg",
                file_name=f"img_{i}.jpg",
                width=100,
                height=100,
            )
            for i in range(3)
        ],
    )

    # Update two samples to different statuses (metadata vs embedding stages).
    image_resolver.update_status(
        session=db_session,
        sample_ids=[sample_ids[0]],
        status="queued",
        status_field="status_metadata",
    )
    image_resolver.update_status(
        session=db_session,
        sample_ids=[sample_ids[1]],
        status="failed",
        status_field="status_embeddings",
    )
    # Leave the last one as READY (default for both fields).

    counts_metadata = image_resolver.count_by_status(
        session=db_session, dataset_id=dataset.dataset_id, status_field="status_metadata"
    )
    counts_embeddings = image_resolver.count_by_status(
        session=db_session, dataset_id=dataset.dataset_id, status_field="status_embeddings"
    )

    assert counts_metadata["queued"] == 1
    assert counts_metadata["ready"] == 2  # two still ready for metadata
    assert counts_embeddings["failed"] == 1
    assert counts_embeddings["ready"] == 2
