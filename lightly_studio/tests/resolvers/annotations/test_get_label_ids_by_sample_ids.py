"""Tests for retrieving annotation labels associated with samples."""

from uuid import UUID

import pytest
from sqlmodel import Session

from lightly_studio.resolvers import annotation_resolver
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
)


def test_get_label_ids_by_sample_ids__returns_parent_and_own_labels(
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session)
    image = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/path/to/image.png",
    )
    unrelated_image = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/path/to/unrelated.png",
    )
    selected_label = create_annotation_label(
        session=db_session,
        root_collection_id=collection.collection_id,
        label_name="selected",
    )
    unselected_label = create_annotation_label(
        session=db_session,
        root_collection_id=collection.collection_id,
        label_name="unselected",
    )
    selected_annotation = create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=selected_label.annotation_label_id,
    )
    create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=selected_label.annotation_label_id,
    )
    create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=unselected_label.annotation_label_id,
    )
    create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=unrelated_image.sample_id,
        annotation_label_id=selected_label.annotation_label_id,
    )

    result = annotation_resolver.get_label_ids_by_sample_ids(
        session=db_session,
        sample_ids=[image.sample_id, selected_annotation.sample_id],
        annotation_label_ids=[selected_label.annotation_label_id],
    )

    assert result == {
        image.sample_id: {selected_label.annotation_label_id},
        selected_annotation.sample_id: {selected_label.annotation_label_id},
    }


@pytest.mark.parametrize(
    ("sample_ids", "annotation_label_ids"),
    [([], [UUID(int=1)]), ([UUID(int=1)], [])],
)
def test_get_label_ids_by_sample_ids__empty_input(
    db_session: Session,
    sample_ids: list[UUID],
    annotation_label_ids: list[UUID],
) -> None:
    assert (
        annotation_resolver.get_label_ids_by_sample_ids(
            session=db_session,
            sample_ids=sample_ids,
            annotation_label_ids=annotation_label_ids,
        )
        == {}
    )
