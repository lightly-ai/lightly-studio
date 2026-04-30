from __future__ import annotations

from uuid import UUID

import pytest
from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.models.sort import SortFieldSource, SortFieldSpec
from lightly_studio.resolvers import image_resolver
from tests.helpers_resolvers import create_collection


def test_get_sort_field_specs(db_session: Session) -> None:
    collection = create_collection(session=db_session)

    fields = image_resolver.get_sort_field_specs(
        session=db_session,
        dataset_id=collection.dataset_id,
    )

    assert fields == [
        SortFieldSpec(
            id="image.file_name",
            field_name="file_name",
            label="File Name",
            source=SortFieldSource.IMAGE,
        ),
        SortFieldSpec(
            id="image.file_path_abs",
            field_name="file_path_abs",
            label="File Path",
            source=SortFieldSource.IMAGE,
        ),
        SortFieldSpec(
            id="image.width",
            field_name="width",
            label="Width",
            source=SortFieldSource.IMAGE,
        ),
        SortFieldSpec(
            id="image.height",
            field_name="height",
            label="Height",
            source=SortFieldSource.IMAGE,
        ),
        SortFieldSpec(
            id="sample.created_at",
            field_name="created_at",
            label="Created At",
            source=SortFieldSource.SAMPLE,
        ),
    ]


def test_get_sort_field_specs__non_existent_dataset(db_session: Session) -> None:
    dataset_id = UUID("00000000-0000-0000-0000-000000000000")

    with pytest.raises(ValueError, match=rf"Dataset with id {dataset_id} not found\."):
        image_resolver.get_sort_field_specs(session=db_session, dataset_id=dataset_id)


def test_get_sort_field_specs__non_image_dataset(db_session: Session) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)

    with pytest.raises(ValueError, match=rf"Dataset {collection.dataset_id} is not an image"):
        image_resolver.get_sort_field_specs(
            session=db_session,
            dataset_id=collection.dataset_id,
        )
