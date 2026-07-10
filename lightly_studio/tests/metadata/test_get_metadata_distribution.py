"""Tests for the metadata distribution resolver."""

from __future__ import annotations

from uuid import UUID

import pytest
from sqlmodel import Session

from lightly_studio.errors import (
    MetadataKeyNotFoundError,
    UnsupportedMetadataTypeError,
)
from lightly_studio.metadata.gps_coordinate import GPSCoordinate
from lightly_studio.resolvers.metadata_resolver.sample.get_metadata_distribution import (
    NONE_LABEL,
    get_metadata_distribution,
)
from tests.helpers_resolvers import create_collection, create_image


def _add_sample(session: Session, collection_id: UUID, path: str, **metadata: object) -> UUID:
    sample = create_image(session=session, collection_id=collection_id, file_path_abs=path).sample
    for key, value in metadata.items():
        sample[key] = value
    return sample.sample_id


def test_categorical_distribution__counts_and_none(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    _add_sample(db_session, collection_id, "/a.png", location="city")
    _add_sample(db_session, collection_id, "/b.png", location="city")
    _add_sample(db_session, collection_id, "/c.png", location="mountain")
    _add_sample(db_session, collection_id, "/d.png")  # missing the key

    result = get_metadata_distribution(
        session=db_session, collection_id=collection_id, key="location"
    )

    assert result.kind == "categorical"
    assert result.type == "string"
    assert result.categorical is not None
    as_dict = {item.value: item.count for item in result.categorical}
    assert as_dict == {"city": 2, "mountain": 1, NONE_LABEL: 1}
    # Highest count first, with the (none) entry last.
    assert result.categorical[0].value == "city"
    assert result.categorical[-1].value == NONE_LABEL


def test_categorical_distribution__boolean_labels(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    _add_sample(db_session, collection_id, "/a.png", flag=True)
    _add_sample(db_session, collection_id, "/b.png", flag=False)
    _add_sample(db_session, collection_id, "/c.png", flag=False)

    result = get_metadata_distribution(
        session=db_session, collection_id=collection_id, key="flag"
    )

    assert result.type == "boolean"
    as_dict = {item.value: item.count for item in result.categorical or []}
    assert as_dict == {"true": 1, "false": 2, NONE_LABEL: 0}


def test_categorical_distribution__respects_scope(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    city = _add_sample(db_session, collection_id, "/a.png", location="city")
    _add_sample(db_session, collection_id, "/b.png", location="mountain")
    missing = _add_sample(db_session, collection_id, "/c.png")

    result = get_metadata_distribution(
        session=db_session,
        collection_id=collection_id,
        key="location",
        scope_sample_ids={city, missing},
    )

    as_dict = {item.value: item.count for item in result.categorical or []}
    assert as_dict == {"city": 1, NONE_LABEL: 1}


def test_numeric_distribution__equal_width_bins(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    for index, value in enumerate([0.0, 5.0, 10.0]):
        _add_sample(db_session, collection_id, f"/{index}.png", score=value)
    _add_sample(db_session, collection_id, "/none.png")  # missing the key

    result = get_metadata_distribution(
        session=db_session, collection_id=collection_id, key="score", bins=2
    )

    assert result.kind == "numeric"
    assert result.type == "float"
    assert result.bin_edges == pytest.approx([0.0, 5.0, 10.0])
    # Half-open bins [0,5),[5,10]: 0.0 in bin 0; 5.0 and (clamped) 10.0 in bin 1.
    assert result.counts == [1, 2]
    assert result.none_count == 1


def test_numeric_distribution__edges_use_global_range_not_scope(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    low = _add_sample(db_session, collection_id, "/low.png", score=0.0)
    _add_sample(db_session, collection_id, "/mid.png", score=50.0)
    _add_sample(db_session, collection_id, "/high.png", score=100.0)

    result = get_metadata_distribution(
        session=db_session,
        collection_id=collection_id,
        key="score",
        scope_sample_ids={low},
        bins=4,
    )

    # Edges span the global [0, 100] range even though only one sample is in scope.
    assert result.bin_edges == pytest.approx([0.0, 25.0, 50.0, 75.0, 100.0])
    assert result.counts == [1, 0, 0, 0]
    assert result.none_count == 0


def test_numeric_distribution__single_value_range(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    _add_sample(db_session, collection_id, "/a.png", score=7.0)
    _add_sample(db_session, collection_id, "/b.png", score=7.0)

    result = get_metadata_distribution(
        session=db_session, collection_id=collection_id, key="score", bins=3
    )

    assert result.bin_edges is not None
    assert result.bin_edges[0] == pytest.approx(7.0)
    assert sum(result.counts or []) == 2


def test_missing_key_raises(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    _add_sample(db_session, collection_id, "/a.png", location="city")

    with pytest.raises(MetadataKeyNotFoundError):
        get_metadata_distribution(
            session=db_session, collection_id=collection_id, key="does_not_exist"
        )


def test_unsupported_type_raises(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    _add_sample(
        db_session, collection_id, "/a.png", location_gps=GPSCoordinate(lat=1.0, lon=2.0)
    )

    with pytest.raises(UnsupportedMetadataTypeError):
        get_metadata_distribution(
            session=db_session, collection_id=collection_id, key="location_gps"
        )
