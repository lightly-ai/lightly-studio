from __future__ import annotations

from sqlmodel import Session, select

from lightly_studio.core.dataset_query.classification_expression import (
    ClassificationField,
    ClassificationQuery,
)
from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
)


class TestClassificationExpressions:
    def test_annotation_classification_label__sql(self) -> None:
        query = select(ImageTable).where(
            ClassificationQuery.match(ClassificationField.label == "cat").get()
        )
        sql = str(query.compile(compile_kwargs={"literal_binds": True}))
        assert "EXISTS (SELECT 1" in sql
        assert "FROM annotation_base" in sql
        assert "annotation_type = 'CLASSIFICATION'" in sql
        assert "annotation_label.annotation_label_name = 'cat'" in sql

    def test_annotation_classification__filters_matching_samples(self, db_session: Session) -> None:
        collection = create_collection(session=db_session)
        collection_id = collection.collection_id
        image1 = create_image(
            session=db_session, collection_id=collection_id, file_path_abs="/path/to/1.jpg"
        )
        image2 = create_image(
            session=db_session, collection_id=collection_id, file_path_abs="/path/to/2.jpg"
        )
        label1 = create_annotation_label(
            session=db_session, root_collection_id=collection_id, label_name="label1"
        )
        label2 = create_annotation_label(
            session=db_session, root_collection_id=collection_id, label_name="label2"
        )

        create_annotation(
            session=db_session,
            collection_id=collection_id,
            sample_id=image1.sample_id,
            annotation_label_id=label1.annotation_label_id,
            annotation_type=AnnotationType.CLASSIFICATION,
        )
        create_annotation(
            session=db_session,
            collection_id=collection_id,
            sample_id=image2.sample_id,
            annotation_label_id=label2.annotation_label_id,
            annotation_type=AnnotationType.CLASSIFICATION,
        )

        query = (
            select(ImageTable)
            .join(ImageTable.sample)
            .where(SampleTable.collection_id == collection_id)
            .where(ClassificationQuery.match(ClassificationField.label == "label1").get())
        )
        results = db_session.exec(query).all()
        assert [image.sample_id for image in results] == [image1.sample_id]

    def test_annotation_classification__with_other_annotations(self, db_session: Session) -> None:
        collection = create_collection(session=db_session)
        collection_id = collection.collection_id
        image1 = create_image(
            session=db_session, collection_id=collection_id, file_path_abs="/path/to/1.jpg"
        )
        image2 = create_image(
            session=db_session, collection_id=collection_id, file_path_abs="/path/to/2.jpg"
        )
        label1 = create_annotation_label(
            session=db_session, root_collection_id=collection_id, label_name="label1"
        )

        create_annotation(
            session=db_session,
            collection_id=collection_id,
            sample_id=image1.sample_id,
            annotation_label_id=label1.annotation_label_id,
            annotation_type=AnnotationType.CLASSIFICATION,
        )
        create_annotation(
            session=db_session,
            collection_id=collection_id,
            sample_id=image2.sample_id,
            annotation_label_id=label1.annotation_label_id,
            annotation_type=AnnotationType.OBJECT_DETECTION,
            annotation_data={"x": 0, "y": 0, "width": 150, "height": 100},
        )

        query = (
            select(ImageTable)
            .join(ImageTable.sample)
            .where(SampleTable.collection_id == collection_id)
            .where(ClassificationQuery.match().get())
        )
        results = db_session.exec(query).all()
        # There are two annotations but only one of the right type.
        assert [image.sample_id for image in results] == [image1.sample_id]
