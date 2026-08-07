"""Test resolving the value type of metadata sorts."""

from __future__ import annotations

from uuid import UUID

import pytest
from sqlmodel import Session

from lightly_studio.core.dataset_query.image_sample_field import ImageSampleField
from lightly_studio.core.dataset_query.order_by import OrderByField, OrderByMetadataField
from lightly_studio.resolvers import metadata_resolver
from lightly_studio.resolvers.metadata_resolver.sample import metadata_sort_types
from tests.helpers_resolvers import create_collection, create_image


def _create_collection_with_metadata(session: Session) -> UUID:
    """Create a collection holding one sample with one metadata key per type."""
    collection = create_collection(session=session)
    collection_id = collection.collection_id
    image = create_image(
        session=session, collection_id=collection_id, file_path_abs="/images/a.png"
    )
    metadata_resolver.bulk_update_metadata(
        session,
        [
            (
                image.sample_id,
                {
                    "count": 3,
                    "score": 1.5,
                    "label": "cat",
                    "is_valid": True,
                },
            )
        ],
    )
    return collection_id


@pytest.mark.parametrize(
    ("metadata_key", "expected_cast_to_float"),
    [
        ("count", True),  # Integer.
        ("score", True),  # Float.
        ("label", False),  # String.
        ("is_valid", False),  # Boolean.
        ("does_not_exist", False),  # Absent from the schema.
    ],
)
def test_resolve_cast_to_float(
    db_session: Session, metadata_key: str, expected_cast_to_float: bool
) -> None:
    collection_id = _create_collection_with_metadata(session=db_session)
    order_by = OrderByMetadataField(metadata_key)

    metadata_sort_types.resolve_cast_to_float(
        session=db_session, collection_id=collection_id, order_by=[order_by]
    )

    assert order_by.cast_to_float is expected_cast_to_float


def test_resolve_cast_to_float__resets_stale_cast(db_session: Session) -> None:
    """An explicitly passed cast is overruled by the recorded schema type."""
    collection_id = _create_collection_with_metadata(session=db_session)
    order_by = OrderByMetadataField("label", cast_to_float=True)

    metadata_sort_types.resolve_cast_to_float(
        session=db_session, collection_id=collection_id, order_by=[order_by]
    )

    assert order_by.cast_to_float is False


def test_resolve_cast_to_float__other_collection(db_session: Session) -> None:
    """A key present in another collection is not used for this one."""
    _create_collection_with_metadata(session=db_session)
    other_collection = create_collection(session=db_session, collection_name="other_collection")
    order_by = OrderByMetadataField("count")

    metadata_sort_types.resolve_cast_to_float(
        session=db_session,
        collection_id=other_collection.collection_id,
        order_by=[order_by],
    )

    assert order_by.cast_to_float is False


def test_resolve_cast_to_float__multiple_expressions(db_session: Session) -> None:
    """Every metadata sort is resolved; other expression types are left untouched."""
    collection_id = _create_collection_with_metadata(session=db_session)
    numeric_order_by = OrderByMetadataField("count")
    string_order_by = OrderByMetadataField("label")
    field_order_by = OrderByField(ImageSampleField.file_name)

    metadata_sort_types.resolve_cast_to_float(
        session=db_session,
        collection_id=collection_id,
        order_by=[numeric_order_by, string_order_by, field_order_by],
    )

    assert numeric_order_by.cast_to_float is True
    assert string_order_by.cast_to_float is False
    assert field_order_by.field is ImageSampleField.file_name
