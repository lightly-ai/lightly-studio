from __future__ import annotations

from sqlmodel import Session

from lightly_studio.resolvers import collection_resolver
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
)


def test_get_parent_collection_id__from_parent_collection(test_db: Session) -> None:
    collection = create_collection(session=test_db)

    image_1 = create_image(
        session=test_db,
        collection_id=collection.collection_id,
        file_path_abs="/path/to/sample2.png",
    )
    car_label = create_annotation_label(
        session=test_db,
        root_collection_id=collection.collection_id,
        label_name="car",
    )
    annotation = create_annotation(
        session=test_db,
        sample_id=image_1.sample_id,
        annotation_label_id=car_label.annotation_label_id,
        collection_id=collection.collection_id,
    )

    parent_collection = collection_resolver.get_parent_collection_id(
        session=test_db, collection_id=annotation.sample.collection_id
    )
    assert parent_collection is not None
    assert parent_collection.collection_id == collection.collection_id


def test_get_parent_collection_id__from_root_collection(test_db: Session) -> None:
    collection = create_collection(session=test_db)

    parent_collection = collection_resolver.get_parent_collection_id(
        session=test_db, collection_id=collection.collection_id
    )
    assert parent_collection is None
