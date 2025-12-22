"""Tests for updating segmentation mask of annotation instance segmentation."""

from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationCreate, AnnotationType
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import annotation_resolver
from lightly_studio.services import annotations_service
from tests.helpers_resolvers import create_annotation_label, create_collection, create_image


def test_update_segmentation_mask(test_db: Session) -> None:
    collection = create_collection(session=test_db, sample_type=SampleType.IMAGE)
    collection_id = collection.collection_id

    car_label = create_annotation_label(
        session=test_db,
        dataset_id=collection_id,
        label_name="car",
    )

    image = create_image(
        session=test_db,
        collection_id=collection_id,
        file_path_abs="/path/to/sample2.png",
    )

    annotation_id = annotation_resolver.create_many(
        session=test_db,
        parent_collection_id=collection_id,
        annotations=[
            AnnotationCreate(
                parent_sample_id=image.sample_id,
                annotation_label_id=car_label.annotation_label_id,
                annotation_type=AnnotationType.INSTANCE_SEGMENTATION,
                x=50,
                y=50,
                width=20,
                height=20,
                segmentation_mask=[0, 2, 4, 6, 8],
            )
        ],
    )[0]

    annotation = annotations_service.update_segmentation_mask(
        session=test_db, annotation_id=annotation_id, segmentation_mask=[1, 2, 3, 4]
    )

    assert annotation.sample_id == annotation_id
    assert annotation.instance_segmentation_details is not None
    assert annotation.instance_segmentation_details.segmentation_mask == [1, 2, 3, 4]
