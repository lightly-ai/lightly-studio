from __future__ import annotations

from sqlmodel import Session, select

from lightly_studio.core.dataset_query.polygon_query import PolygonField, PolygonQuery
from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.annotation.polygon import Polygons
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
)

NARROW_POLYGON: Polygons = [[(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]]
WIDE_POLYGON: Polygons = [[(0.0, 0.0), (50.0, 0.0), (50.0, 10.0), (0.0, 10.0)]]


class TestPolygonQuery:
    def test_get__width_sql(self) -> None:
        query = select(ImageTable).where(PolygonQuery(PolygonField.width <= 100).get())
        sql = str(query.compile(compile_kwargs={"literal_binds": True}))
        assert "EXISTS (SELECT 1" in sql
        assert "FROM annotation_base" in sql
        assert "FROM polygon_annotation" in sql
        assert "polygon_annotation.width <= 100" in sql

    def test_get__width(self, db_session: Session) -> None:
        collection_id = create_collection(session=db_session).collection_id
        image1 = create_image(
            session=db_session, collection_id=collection_id, file_path_abs="/path/to/1.jpg"
        )
        image2 = create_image(
            session=db_session, collection_id=collection_id, file_path_abs="/path/to/2.jpg"
        )
        label = create_annotation_label(
            session=db_session, root_collection_id=collection_id, label_name="label1"
        )
        create_annotation(
            session=db_session,
            collection_id=collection_id,
            sample_id=image1.sample_id,
            annotation_label_id=label.annotation_label_id,
            annotation_type=AnnotationType.POLYGON,
            annotation_data={"x": 0, "y": 0, "width": 10, "height": 10},
            polygons=NARROW_POLYGON,
        )
        create_annotation(
            session=db_session,
            collection_id=collection_id,
            sample_id=image2.sample_id,
            annotation_label_id=label.annotation_label_id,
            annotation_type=AnnotationType.POLYGON,
            annotation_data={"x": 0, "y": 0, "width": 50, "height": 10},
            polygons=WIDE_POLYGON,
        )

        query = (
            select(ImageTable)
            .join(ImageTable.sample)
            .where(SampleTable.collection_id == collection_id)
            .where(PolygonQuery(PolygonField.width > 20).get())
        )
        results = db_session.exec(query).all()
        assert [image.sample_id for image in results] == [image2.sample_id]

    def test_get__ignores_masks(self, db_session: Session) -> None:
        collection_id = create_collection(session=db_session).collection_id
        image = create_image(
            session=db_session, collection_id=collection_id, file_path_abs="/path/to/1.jpg"
        )
        label = create_annotation_label(
            session=db_session, root_collection_id=collection_id, label_name="label1"
        )
        create_annotation(
            session=db_session,
            collection_id=collection_id,
            sample_id=image.sample_id,
            annotation_label_id=label.annotation_label_id,
            annotation_type=AnnotationType.SEGMENTATION_MASK,
            annotation_data={"x": 0, "y": 0, "width": 50, "height": 10, "segmentation_mask": [6]},
        )

        query = (
            select(ImageTable)
            .join(ImageTable.sample)
            .where(SampleTable.collection_id == collection_id)
            .where(PolygonQuery(PolygonField.class_name == "label1").get())
        )
        assert db_session.exec(query).all() == []
