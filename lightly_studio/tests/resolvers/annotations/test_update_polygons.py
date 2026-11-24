import pytest
from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.annotation.polygon import Polygons
from lightly_studio.resolvers import annotation_resolver
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
)

TRIANGLE: Polygons = [[(0, 0), (2, 0), (2, 2)]]


def test_update_polygons__replaces_and_recomputes_box(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    label = create_annotation_label(session=db_session, root_collection_id=collection_id)
    image = create_image(session=db_session, collection_id=collection_id)
    annotation = create_annotation(
        session=db_session,
        collection_id=collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.POLYGON,
        polygons=TRIANGLE,
    )

    updated = annotation_resolver.update_polygons(
        session=db_session,
        annotation_id=annotation.sample_id,
        polygons=[[(0, 0), (2, 0), (2, 2)], [(5, 5), (9, 5), (9, 7)]],
    )

    assert updated.polygon_details is not None
    assert updated.polygon_details.polygons == [
        [[0, 0], [2, 0], [2, 2]],
        [[5, 5], [9, 5], [9, 7]],
    ]
    assert (updated.polygon_details.x, updated.polygon_details.y) == (0, 0)
    assert (updated.polygon_details.width, updated.polygon_details.height) == (9, 7)


def test_update_polygons__invalid_keeps_old(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    label = create_annotation_label(session=db_session, root_collection_id=collection_id)
    image = create_image(session=db_session, collection_id=collection_id)
    annotation = create_annotation(
        session=db_session,
        collection_id=collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.POLYGON,
        polygons=TRIANGLE,
    )

    with pytest.raises(ValueError, match="at least 3 vertices"):
        annotation_resolver.update_polygons(
            session=db_session,
            annotation_id=annotation.sample_id,
            polygons=[[(0, 0), (9, 9)]],
        )

    stored = annotation_resolver.get_by_id(session=db_session, annotation_id=annotation.sample_id)
    assert stored is not None
    assert stored.polygon_details is not None
    assert stored.polygon_details.polygons == [[[0, 0], [2, 0], [2, 2]]]
    assert stored.polygon_details.width == 2


def test_update_polygons__not_a_polygon(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    label = create_annotation_label(session=db_session, root_collection_id=collection_id)
    image = create_image(session=db_session, collection_id=collection_id)
    annotation = create_annotation(
        session=db_session,
        collection_id=collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.OBJECT_DETECTION,
    )

    with pytest.raises(ValueError, match=r"Annotation type does not support polygons."):
        annotation_resolver.update_polygons(
            session=db_session, annotation_id=annotation.sample_id, polygons=TRIANGLE
        )
