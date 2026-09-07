from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from sqlmodel import Session, col, select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable, AnnotationType
from lightly_studio.models.annotation.object_detection import ObjectDetectionAnnotationTable
from lightly_studio.models.annotation.segmentation import SegmentationAnnotationTable
from lightly_studio.models.annotation_collection_coverage import AnnotationCollectionCoverageTable
from lightly_studio.models.collection import SampleType
from lightly_studio.models.sample import SampleTable, SampleTagLinkTable
from lightly_studio.models.sample_embedding import SampleEmbeddingTable
from lightly_studio.models.temporal_span import TemporalSpanTable
from lightly_studio.resolvers import annotation_resolver, collection_resolver
from tests.helpers_resolvers import (
    AnnotationDetails,
    ImageStub,
    create_annotation_label,
    create_annotations,
    create_collection,
    create_embedding_model,
    create_images,
    create_sample_embedding,
    create_tag,
)


def test_bulk_delete_annotations__deletes_all_annotation_types_and_children(
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session)
    images = create_images(
        db_session=db_session,
        collection_id=collection.collection_id,
        images=[ImageStub(path="a.png"), ImageStub(path="b.png"), ImageStub(path="c.png")],
    )
    label = create_annotation_label(
        session=db_session,
        root_collection_id=collection.collection_id,
        label_name="dog",
    )
    annotations = create_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        collection_name="ground_truth",
        annotations=[
            AnnotationDetails(
                sample_id=images[0].sample_id,
                annotation_label_id=label.annotation_label_id,
                annotation_type=AnnotationType.CLASSIFICATION,
                start_time_s=0,
                end_time_s=1,
            ),
            AnnotationDetails(
                sample_id=images[1].sample_id,
                annotation_label_id=label.annotation_label_id,
                annotation_type=AnnotationType.OBJECT_DETECTION,
            ),
            AnnotationDetails(
                sample_id=images[2].sample_id,
                annotation_label_id=label.annotation_label_id,
                annotation_type=AnnotationType.SEGMENTATION_MASK,
                segmentation_mask=[1, 0, 1, 0],
            ),
        ],
    )
    annotation_collection_id = annotations[0].sample.collection_id
    tag = create_tag(
        session=db_session,
        collection_id=annotation_collection_id,
        tag_name="annotation-tag",
        kind="annotation",
    )
    embedding_model = create_embedding_model(
        session=db_session,
        collection_id=annotation_collection_id,
        embedding_dimension=2,
    )
    for annotation in annotations:
        annotation.sample.tags.append(tag)
        create_sample_embedding(
            session=db_session,
            sample_id=annotation.sample_id,
            embedding_model_id=embedding_model.embedding_model_id,
            embedding=[0.1, 0.2],
        )
    db_session.commit()
    annotation_ids = [annotation.sample_id for annotation in annotations]
    coverage_before = _coverage_rows(db_session)

    deleted_count = annotation_resolver.bulk_delete_annotations(
        session=db_session,
        collection_id=annotation_collection_id,
        annotation_ids=annotation_ids,
    )

    assert deleted_count == 3
    assert db_session.exec(select(AnnotationBaseTable)).all() == []
    assert db_session.exec(select(ObjectDetectionAnnotationTable)).all() == []
    assert db_session.exec(select(SegmentationAnnotationTable)).all() == []
    assert db_session.exec(select(TemporalSpanTable)).all() == []
    assert db_session.exec(select(SampleTagLinkTable)).all() == []
    assert db_session.exec(select(SampleEmbeddingTable)).all() == []
    assert not db_session.exec(
        select(SampleTable).where(col(SampleTable.sample_id).in_(annotation_ids))
    ).all()
    assert _coverage_rows(db_session) == coverage_before


def test_bulk_delete_annotations__rejects_out_of_collection_id_and_deletes_nothing(
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session)
    other_collection = create_collection(
        session=db_session,
        parent_collection_id=collection.collection_id,
        sample_type=SampleType.ANNOTATION,
        collection_name="other",
    )
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
    annotations = create_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        collection_name="ground_truth",
        annotations=[
            AnnotationDetails(
                sample_id=image.sample_id,
                annotation_label_id=label.annotation_label_id,
            )
        ],
    )
    annotation_id = annotations[0].sample_id

    with pytest.raises(ValueError, match="requested collection"):
        annotation_resolver.bulk_delete_annotations(
            session=db_session,
            collection_id=other_collection.collection_id,
            annotation_ids=[annotation_id],
        )

    assert db_session.get(AnnotationBaseTable, annotation_id) is not None
    assert db_session.get(SampleTable, annotation_id) is not None


def test_bulk_delete_annotations__dedupes_and_allows_empty_list(db_session: Session) -> None:
    collection = create_collection(session=db_session)
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
    annotations = create_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        collection_name="ground_truth",
        annotations=[
            AnnotationDetails(
                sample_id=image.sample_id,
                annotation_label_id=label.annotation_label_id,
            )
        ],
    )
    annotation_id = annotations[0].sample_id

    assert annotation_resolver.bulk_delete_annotations(
        session=db_session,
        collection_id=annotations[0].sample.collection_id,
        annotation_ids=[],
    ) == 0
    assert annotation_resolver.bulk_delete_annotations(
        session=db_session,
        collection_id=annotations[0].sample.collection_id,
        annotation_ids=[annotation_id, annotation_id],
    ) == 1


def test_bulk_delete_annotations__rejects_unknown_id(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    annotation_collection_id = collection_resolver.get_or_create_child_collection(
        session=db_session,
        collection_id=collection.collection_id,
        sample_type=SampleType.ANNOTATION,
    )

    with pytest.raises(ValueError, match="requested collection"):
        annotation_resolver.bulk_delete_annotations(
            session=db_session,
            collection_id=annotation_collection_id,
            annotation_ids=[uuid4()],
        )


def _coverage_rows(session: Session) -> set[tuple[UUID, UUID]]:
    return {
        (row.annotation_collection_id, row.parent_sample_id)
        for row in session.exec(select(AnnotationCollectionCoverageTable)).all()
    }
