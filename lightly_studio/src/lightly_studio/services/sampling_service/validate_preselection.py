"""Validation for sampling preselection."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlmodel import Session

from lightly_studio.resolvers import tag_resolver


def validate_preselection(
    session: Session,
    collection_id: UUID,
    preselected_tag_id: UUID | None,
    input_sample_ids: Sequence[UUID],
    n_samples_to_select: int,
) -> str | None:
    """Validate preselection and return its sample tag name."""
    if preselected_tag_id is None:
        _validate_candidate_count(
            n_candidates=len(input_sample_ids),
            n_samples_to_select=n_samples_to_select,
            has_preselection=False,
        )
        return None

    tag = tag_resolver.get_by_id(session=session, tag_id=preselected_tag_id)
    if tag is None or tag.collection_id != collection_id or tag.kind != "sample":
        raise ValueError("Invalid preselected sample tag.")

    preselected_sample_ids = tag_resolver.get_sample_ids_by_tag_id(
        session=session, tag_id=preselected_tag_id
    )
    if not set(preselected_sample_ids).issubset(input_sample_ids):
        raise ValueError("All samples in the preselected tag must match the current filters.")
    _validate_candidate_count(
        n_candidates=len(input_sample_ids) - len(preselected_sample_ids),
        n_samples_to_select=n_samples_to_select,
        has_preselection=True,
    )
    return tag.name


def _validate_candidate_count(
    n_candidates: int,
    n_samples_to_select: int,
    has_preselection: bool,
) -> None:
    """Raise an error when too few samples remain for sampling."""
    if n_candidates >= n_samples_to_select:
        return
    preselection_note = " after excluding preselected samples" if has_preselection else ""
    raise ValueError(
        f"Cannot select {n_samples_to_select} samples; only {n_candidates} samples are "
        f"available{preselection_note}."
    )
