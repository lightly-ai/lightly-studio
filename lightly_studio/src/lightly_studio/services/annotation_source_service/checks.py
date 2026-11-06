"""Checks for the annotation source operations."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.errors import AnnotationSourceInUseError
from lightly_studio.models.collection import CollectionTable, SampleType
from lightly_studio.resolvers import evaluation_run_resolver


def check_not_in_use(session: Session, source: CollectionTable) -> None:
    """Check that the annotation source can be deleted.

    Raises:
        AnnotationSourceInUseError: If evaluation runs use the annotation source or if it has
            child collections other than captions.
    """
    evaluation_run_names = evaluation_run_resolver.get_names_by_collection_id(
        session=session, collection_id=source.collection_id
    )
    if evaluation_run_names:
        raise AnnotationSourceInUseError(
            f"The annotation source '{source.name}' is used by the evaluation runs "
            f"{', '.join(evaluation_run_names)}. Delete these evaluation runs first."
        )
    # The delete removes the captions of the annotations, but no other attached data.
    child_names = sorted(
        child.name for child in source.children if child.sample_type != SampleType.CAPTION
    )
    if child_names:
        raise AnnotationSourceInUseError(
            f"The annotation source '{source.name}' cannot be deleted because "
            f"it has data attached: {', '.join(child_names)}."
        )
