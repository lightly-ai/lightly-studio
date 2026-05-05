from uuid import UUID

import pytest
from sqlmodel import Session, col, select

from lightly_studio.models.sample import SampleTable, SampleTagLinkTable
from lightly_studio.resolvers import annotation_resolver
from tests.conftest import AnnotationsTestData
from tests.helpers_resolvers import create_tag


def test_delete_annotation__success(
    db_session: Session,
    annotations_test_data: AnnotationsTestData,  # noqa: ARG001
) -> None:
    """Test deleting an annotation."""
    annotations = annotation_resolver.get_all(db_session).annotations

    annotation_ids_to_delete = [
        annotations[0].sample_id,  # classification
        annotations[3].sample_id,  # object detection
        annotations[6].sample_id,  # segmentation mask
    ]

    for annotation_id in annotation_ids_to_delete:
        annotation_resolver.delete_annotation(db_session, annotation_id)

        # Verify the change persisted in the database.
        deleted_annotation = annotation_resolver.get_by_id(db_session, annotation_id)
        assert deleted_annotation is None


def test_delete_annotation__raises_error_when_annotation_not_found(
    db_session: Session,
) -> None:
    """Test that delete_annotation raises ValueError when annotation is not found."""
    non_existent_annotation_id = UUID("12345678-1234-5678-1234-567812345678")

    # Call the resolver and expect ValueError
    with pytest.raises(ValueError, match=f"Annotation {non_existent_annotation_id} not found"):
        annotation_resolver.delete_annotation(db_session, non_existent_annotation_id)


def test_delete_annotation__deletes_sample_tag_links(
    db_session: Session,
    annotations_test_data: AnnotationsTestData,
) -> None:
    """Test deleting an annotation also removes tag links for its sample."""
    annotation = annotations_test_data.annotations[0]
    annotation_collection_id = annotation.sample.collection_id
    tag = create_tag(
        session=db_session,
        collection_id=annotation_collection_id,
        tag_name="annotation-tag",
        kind="annotation",
    )
    annotation.sample.tags.append(tag)
    db_session.add(annotation.sample)
    db_session.commit()

    # Verify there is at least one link before deletion.
    links_before = db_session.exec(
        select(SampleTagLinkTable).where(col(SampleTagLinkTable.sample_id) == annotation.sample_id)
    ).all()
    assert links_before

    annotation_resolver.delete_annotation(db_session, annotation.sample_id)

    # Verify both annotation and sample-tag links were deleted.
    assert annotation_resolver.get_by_id(db_session, annotation.sample_id) is None
    links_after = db_session.exec(
        select(SampleTagLinkTable).where(col(SampleTagLinkTable.sample_id) == annotation.sample_id)
    ).all()
    assert not links_after
    assert db_session.get(SampleTable, annotation.sample_id) is None
