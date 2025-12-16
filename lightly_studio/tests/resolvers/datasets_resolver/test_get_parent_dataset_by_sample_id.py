from __future__ import annotations

from sqlmodel import Session

from lightly_studio.resolvers import collection_resolver
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_dataset,
    create_image,
)


def test_get_parent_by_sample_id(test_db: Session) -> None:
    dataset = create_dataset(session=test_db)

    image_1 = create_image(
        session=test_db,
        dataset_id=dataset.dataset_id,
        file_path_abs="/path/to/sample1.png",
    )
    car_label = create_annotation_label(
        session=test_db,
        annotation_label_name="car",
    )
    annotation = create_annotation(
        session=test_db,
        sample_id=image_1.sample_id,
        annotation_label_id=car_label.annotation_label_id,
        dataset_id=dataset.dataset_id,
    )

    parent_dataset = collection_resolver.get_parent_dataset_by_sample_id(
        session=test_db, sample_id=annotation.sample.sample_id
    )
    assert parent_dataset is not None
    assert parent_dataset.dataset_id == dataset.dataset_id


def test_get_parent_by_sample_id__with_no_parent(test_db: Session) -> None:
    dataset = create_dataset(session=test_db)

    image_1 = create_image(
        session=test_db,
        dataset_id=dataset.dataset_id,
        file_path_abs="/path/to/sample1.png",
    )

    parent_dataset = collection_resolver.get_parent_dataset_by_sample_id(
        session=test_db, sample_id=image_1.sample_id
    )
    assert parent_dataset is None
