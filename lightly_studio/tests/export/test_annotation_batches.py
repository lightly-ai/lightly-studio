import pytest
from sqlmodel import Session

from lightly_studio.export import annotation_batches
from lightly_studio.models.annotation.annotation_base import AnnotationType


def test_iter_sample_annotations__classification_with_other_types(db_session: Session) -> None:
    with pytest.raises(ValueError, match="without other annotation types"):
        next(
            annotation_batches.iter_sample_annotations(
                session=db_session,
                samples=[],
                annotation_types=[AnnotationType.CLASSIFICATION, AnnotationType.POLYGON],
                annotation_collection_id=None,
            )
        )
