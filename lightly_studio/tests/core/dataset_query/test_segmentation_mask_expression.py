from __future__ import annotations

from sqlmodel import Session, select

from lightly_studio.core.dataset_query.segmentation_mask_expression import (
    SegmentationMaskField,
    SegmentationMaskQuery,
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


class TestSegmentationMaskExpressions:
    def test_annotation_segmentation_mask_width__sql(self) -> None:
        query = select(ImageTable).where(
            SegmentationMaskQuery.match(SegmentationMaskField.width <= 100).get()
        )
        sql = str(query.compile(compile_kwargs={"literal_binds": True}))
        assert "EXISTS (SELECT 1" in sql
        assert "FROM annotation_base" in sql
        assert "FROM segmentation_annotation" in sql
        assert "segmentation_annotation.width <= 100" in sql

    def test_annotation_segmentation_mask__filters_matching_samples(
        self, db_session: Session
    ) -> None:
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
            annotation_type=AnnotationType.SEGMENTATION_MASK,
            annotation_data={
                "x": 0,
                "y": 0,
                "width": 150,
                "height": 100,
                "segmentation_mask": [1, 1, 4],
            },
        )
        create_annotation(
            session=db_session,
            collection_id=collection_id,
            sample_id=image2.sample_id,
            annotation_label_id=label1.annotation_label_id,
            annotation_type=AnnotationType.SEGMENTATION_MASK,
            annotation_data={"x": 0, "y": 0, "width": 50, "height": 100, "segmentation_mask": [6]},
        )

        query = (
            select(ImageTable)
            .join(ImageTable.sample)
            .where(SampleTable.collection_id == collection_id)
            .where(
                SegmentationMaskQuery.match(
                    SegmentationMaskField.width > 100,
                    SegmentationMaskField.height == 100,
                ).get()
            )
        )
        results = db_session.exec(query).all()
        assert [image.sample_id for image in results] == [image1.sample_id]

    def test_annotation_segmentation_mask__with_other_annotations(
        self, db_session: Session
    ) -> None:
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
            annotation_type=AnnotationType.SEGMENTATION_MASK,
            annotation_data={"x": 0, "y": 0, "width": 150, "height": 100, "segmentation_mask": [8]},
        )
        create_annotation(
            session=db_session,
            collection_id=collection_id,
            sample_id=image2.sample_id,
            annotation_label_id=label1.annotation_label_id,
            annotation_type=AnnotationType.OBJECT_DETECTION,
            annotation_data={"x": 0, "y": 0, "width": 150, "height": 100, "segmentation_mask": [6]},
        )

        query = (
            select(ImageTable)
            .join(ImageTable.sample)
            .where(SampleTable.collection_id == collection_id)
            .where(SegmentationMaskQuery.match(SegmentationMaskField.label == "label1").get())
        )
        results = db_session.exec(query).all()
        # There are two annotations with this label but only one of the right type.
        assert [image.sample_id for image in results] == [image1.sample_id]
