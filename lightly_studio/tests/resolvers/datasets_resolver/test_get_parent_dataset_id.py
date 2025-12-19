from __future__ import annotations

from sqlmodel import Session

from lightly_studio.resolvers import collection_resolver
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
)


def test_get_parent_dataset_id__from_parent_dataset(test_db: Session) -> None:
    dataset = create_collection(session=test_db)

    image_1 = create_image(
        session=test_db,
        collection_id=dataset.collection_id,
        file_path_abs="/path/to/sample2.png",
    )
    car_label = create_annotation_label(
        session=test_db,
        root_dataset_id=dataset.dataset_id,
        label_name="car",
    )
    annotation = create_annotation(
        session=test_db,
        sample_id=image_1.sample_id,
        annotation_label_id=car_label.annotation_label_id,
        collection_id=dataset.collection_id,
    )

    parent_dataset = collection_resolver.get_parent_collection_id(
        session=test_db, collection_id=annotation.sample.collection_id
    )
    assert parent_dataset is not None
    assert parent_dataset.collection_id == dataset.collection_id


def test_get_parent_dataset_id__from_root_dataset(test_db: Session) -> None:
    dataset = create_collection(session=test_db)

    parent_dataset = collection_resolver.get_parent_collection_id(
        session=test_db, collection_id=dataset.collection_id
    )
    assert parent_dataset is None
