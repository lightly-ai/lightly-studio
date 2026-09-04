from __future__ import annotations

from sqlmodel import Session, select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable, AnnotationType
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.collection import CollectionTable, SampleType
from lightly_studio.resolvers import annotation_resolver, collection_resolver
from lightly_studio.resolvers.image_filter import ImageFilter
from tests.helpers_resolvers import (
    ImageStub,
    create_annotation,
    create_annotation_label,
    create_images,
)


def test_bulk_create_classifications__creates_classifications(
    db_session: Session,
    collection: CollectionTable,
) -> None:
    images = create_images(
        db_session=db_session,
        collection_id=collection.collection_id,
        images=[ImageStub(path="a.png"), ImageStub(path="b.png")],
    )

    result = annotation_resolver.bulk_create_classifications(
        session=db_session,
        parent_collection_id=collection.collection_id,
        parent_sample_ids=[image.sample_id for image in images],
        class_name="dog",
        annotation_collection_name="ground_truth",
    )

    annotations = _get_annotations(db_session)
    assert result.created_count == 2
    assert result.skipped_count == 0
    assert {annotation.sample_id for annotation in annotations} == set(
        result.created_annotation_ids
    )
    assert {annotation.parent_sample_id for annotation in annotations} == {
        image.sample_id for image in images
    }
    assert {annotation.annotation_type for annotation in annotations} == {
        AnnotationType.CLASSIFICATION
    }
    assert all(annotation.object_detection_details is None for annotation in annotations)
    assert all(annotation.segmentation_details is None for annotation in annotations)


def test_bulk_create_classifications__skips_duplicate_classifications(
    db_session: Session,
    collection: CollectionTable,
) -> None:
    images = create_images(
        db_session=db_session,
        collection_id=collection.collection_id,
        images=[ImageStub(path="a.png"), ImageStub(path="b.png")],
    )
    annotation_resolver.bulk_create_classifications(
        session=db_session,
        parent_collection_id=collection.collection_id,
        parent_sample_ids=[images[0].sample_id],
        class_name="dog",
        annotation_collection_name="ground_truth",
    )

    result = annotation_resolver.bulk_create_classifications(
        session=db_session,
        parent_collection_id=collection.collection_id,
        parent_sample_ids=[images[0].sample_id, images[1].sample_id, images[1].sample_id],
        class_name="dog",
        annotation_collection_name="ground_truth",
    )

    assert result.created_count == 1
    assert result.skipped_count == 1
    assert len(_get_annotations(db_session)) == 2


def test_bulk_create_classifications__object_detection_same_class_does_not_block_classification(
    db_session: Session,
    collection: CollectionTable,
) -> None:
    image = create_images(
        db_session=db_session,
        collection_id=collection.collection_id,
        images=[ImageStub(path="a.png")],
    )[0]
    label = create_annotation_label(
        session=db_session,
        root_collection_id=collection.collection_id,
        label_name="car",
    )
    create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.OBJECT_DETECTION,
        annotation_collection_name="ground_truth",
    )

    result = annotation_resolver.bulk_create_classifications(
        session=db_session,
        parent_collection_id=collection.collection_id,
        parent_sample_ids=[image.sample_id],
        class_name="car",
        annotation_collection_name="ground_truth",
    )

    annotations = _get_annotations(db_session)
    assert result.created_count == 1
    assert result.skipped_count == 0
    assert {annotation.annotation_type for annotation in annotations} == {
        AnnotationType.OBJECT_DETECTION,
        AnnotationType.CLASSIFICATION,
    }


def test_bulk_create_classifications__different_class_and_source_scope_dedupe(
    db_session: Session,
    collection: CollectionTable,
) -> None:
    image = create_images(
        db_session=db_session,
        collection_id=collection.collection_id,
        images=[ImageStub(path="a.png")],
    )[0]
    annotation_resolver.bulk_create_classifications(
        session=db_session,
        parent_collection_id=collection.collection_id,
        parent_sample_ids=[image.sample_id],
        class_name="dog",
        annotation_collection_name="ground_truth",
    )

    other_class = annotation_resolver.bulk_create_classifications(
        session=db_session,
        parent_collection_id=collection.collection_id,
        parent_sample_ids=[image.sample_id],
        class_name="cat",
        annotation_collection_name="ground_truth",
    )
    other_source = annotation_resolver.bulk_create_classifications(
        session=db_session,
        parent_collection_id=collection.collection_id,
        parent_sample_ids=[image.sample_id],
        class_name="dog",
        annotation_collection_name="prediction",
    )

    assert other_class.created_count == 1
    assert other_source.created_count == 1
    assert len(_get_annotations(db_session)) == 3


def test_bulk_create_classifications_from_query__matches_id_list(
    db_session: Session,
    collection: CollectionTable,
) -> None:
    images = create_images(
        db_session=db_session,
        collection_id=collection.collection_id,
        images=[
            ImageStub(path="wide.png", width=1920),
            ImageStub(path="narrow.png", width=10),
        ],
    )
    query = ImageFilter(width={"min": 100}).build_sample_ids_query(
        collection_id=collection.collection_id
    )

    result = annotation_resolver.bulk_create_classifications_from_query(
        session=db_session,
        parent_collection_id=collection.collection_id,
        parent_sample_ids_query=query,
        class_name="dog",
        annotation_collection_name="ground_truth",
    )

    assert result.created_count == 1
    assert _get_annotations(db_session)[0].parent_sample_id == images[0].sample_id


def test_bulk_create_classifications__default_source(
    db_session: Session,
    collection: CollectionTable,
) -> None:
    image = create_images(
        db_session=db_session,
        collection_id=collection.collection_id,
        images=[ImageStub(path="a.png")],
    )[0]
    annotation_resolver.bulk_create_classifications(
        session=db_session,
        parent_collection_id=collection.collection_id,
        parent_sample_ids=[image.sample_id],
        class_name="dog",
    )

    annotation_collection = collection_resolver.get_or_create_child_collection(
        session=db_session,
        collection_id=collection.collection_id,
        sample_type=SampleType.ANNOTATION,
    )
    assert _get_annotations(db_session)[0].sample.collection_id == annotation_collection


def test_bulk_create_classifications__reuses_existing_class(
    db_session: Session,
    collection: CollectionTable,
) -> None:
    image = create_images(
        db_session=db_session,
        collection_id=collection.collection_id,
        images=[ImageStub(path="a.png")],
    )[0]
    label = create_annotation_label(
        session=db_session,
        root_collection_id=collection.collection_id,
        label_name="dog",
    )

    annotation_resolver.bulk_create_classifications(
        session=db_session,
        parent_collection_id=collection.collection_id,
        parent_sample_ids=[image.sample_id],
        class_name="dog",
    )

    labels = list(db_session.exec(select(AnnotationLabelTable)).all())
    assert labels == [label]
    assert _get_annotations(db_session)[0].annotation_label_id == label.annotation_label_id


def _get_annotations(session: Session) -> list[AnnotationBaseTable]:
    return list(session.exec(select(AnnotationBaseTable)).all())
