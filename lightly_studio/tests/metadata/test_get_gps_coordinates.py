"""Tests for the GPS coordinates resolver."""

from __future__ import annotations

from uuid import UUID

import pytest
from sqlmodel import Session

from lightly_studio.errors import (
    MetadataKeyNotFoundError,
    UnsupportedMetadataTypeError,
)
from lightly_studio.metadata.gps_coordinate import GPSCoordinate
from lightly_studio.resolvers import tag_resolver
from lightly_studio.resolvers.metadata_resolver.sample.get_gps_coordinates import (
    get_gps_coordinates,
)
from tests.helpers_resolvers import create_collection, create_image, create_tag


def _add_sample(session: Session, collection_id: UUID, path: str, **metadata: object) -> UUID:
    sample = create_image(session=session, collection_id=collection_id, file_path_abs=path).sample
    for key, value in metadata.items():
        sample[key] = value
    return sample.sample_id


def test_returns_lat_lon_for_gps_samples(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    with_gps = _add_sample(
        db_session, collection_id, "/a.png", gps=GPSCoordinate(lat=47.1, lon=8.2)
    )
    _add_sample(db_session, collection_id, "/b.png")  # no GPS -> omitted

    result = get_gps_coordinates(session=db_session, collection_id=collection_id, key="gps")

    assert len(result) == 1
    point = result[0]
    assert point.sample_id == with_gps
    assert point.lat == pytest.approx(47.1)
    assert point.lon == pytest.approx(8.2)
    assert point.tag_ids == []


def test_attaches_sample_tags(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    sample = create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/a.png"
    ).sample
    sample["gps"] = GPSCoordinate(lat=1.0, lon=2.0)
    tag = create_tag(session=db_session, collection_id=collection_id, tag_name="batch_A")
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session, tag_id=tag.tag_id, sample_ids=[sample.sample_id]
    )

    result = get_gps_coordinates(session=db_session, collection_id=collection_id, key="gps")

    assert len(result) == 1
    assert result[0].tag_ids == [tag.tag_id]


def test_respects_scope(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    kept = _add_sample(db_session, collection_id, "/a.png", gps=GPSCoordinate(lat=1.0, lon=2.0))
    _add_sample(db_session, collection_id, "/b.png", gps=GPSCoordinate(lat=3.0, lon=4.0))

    result = get_gps_coordinates(
        session=db_session, collection_id=collection_id, key="gps", scope_sample_ids={kept}
    )

    assert [point.sample_id for point in result] == [kept]


def test_missing_key_raises(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    _add_sample(db_session, collection_id, "/a.png", gps=GPSCoordinate(lat=1.0, lon=2.0))

    with pytest.raises(MetadataKeyNotFoundError):
        get_gps_coordinates(session=db_session, collection_id=collection_id, key="does_not_exist")


def test_non_gps_key_raises(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    _add_sample(db_session, collection_id, "/a.png", location="city")

    with pytest.raises(UnsupportedMetadataTypeError):
        get_gps_coordinates(session=db_session, collection_id=collection_id, key="location")
