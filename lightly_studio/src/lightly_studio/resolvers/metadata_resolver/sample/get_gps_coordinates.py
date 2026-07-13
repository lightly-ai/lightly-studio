"""Resolver returning per-sample GPS coordinates for the interactive map.

Reads the ``gps_coordinate`` metadata key (stored as ``{"lat", "lon"}``) for
every in-scope sample that has it, and attaches the sample-kind tags each sample
carries so the frontend can color points by tag. Samples without GPS are simply
omitted.
"""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.errors import (
    MetadataKeyNotFoundError,
    UnsupportedMetadataTypeError,
)
from lightly_studio.models.metadata import GPSCoordinateView
from lightly_studio.resolvers import tag_resolver
from lightly_studio.resolvers.metadata_resolver.sample.get_metadata_values_for_key import (
    get_metadata_values_for_key,
)

GPS_METADATA_TYPE = "gps_coordinate"


def get_gps_coordinates(
    session: Session,
    collection_id: UUID,
    key: str,
    *,
    scope_sample_ids: set[UUID] | None = None,
) -> list[GPSCoordinateView]:
    """Return the GPS position and sample tags of every in-scope sample.

    Args:
        session: The database session.
        collection_id: The collection's UUID.
        key: The ``gps_coordinate`` metadata key to read.
        scope_sample_ids: The samples to return. ``None`` returns every sample in
            the collection that has a GPS value.

    Returns:
        One ``GPSCoordinateView`` per in-scope sample that has a GPS value.

    Raises:
        MetadataKeyNotFoundError: If the key is absent from the collection.
        UnsupportedMetadataTypeError: If the key is not a ``gps_coordinate`` key.
    """
    sample_to_value, metadata_type = get_metadata_values_for_key(
        session=session, collection_id=collection_id, key=key
    )
    if metadata_type is None:
        raise MetadataKeyNotFoundError(
            f"Metadata key '{key}' not found in collection {collection_id}."
        )
    if metadata_type != GPS_METADATA_TYPE:
        raise UnsupportedMetadataTypeError(
            f"Metadata key '{key}' has type {metadata_type!r}, expected {GPS_METADATA_TYPE!r}."
        )

    sample_tags = _sample_tags(session=session, collection_id=collection_id)

    points: list[GPSCoordinateView] = []
    for sample_id, value in sample_to_value.items():
        if scope_sample_ids is not None and sample_id not in scope_sample_ids:
            continue
        lat, lon = _parse_lat_lon(value)
        if lat is None or lon is None:
            continue
        points.append(
            GPSCoordinateView(
                sample_id=sample_id,
                lat=lat,
                lon=lon,
                tag_ids=sorted(sample_tags.get(sample_id, set())),
            )
        )
    return points


def _sample_tags(session: Session, collection_id: UUID) -> dict[UUID, set[UUID]]:
    """Return ``{sample_id: {tag_id, ...}}`` for the collection's sample tags."""
    tag_ids = [
        tag.tag_id
        for tag in tag_resolver.get_all_by_collection_id(
            session=session, collection_id=collection_id
        )
        if tag.kind == "sample"
    ]
    return tag_resolver.get_tags_by_sample(session=session, tag_ids=tag_ids)


def _parse_lat_lon(value: object) -> tuple[float | None, float | None]:
    """Extract ``lat``/``lon`` from a stored GPS value (``{"lat", "lon"}``)."""
    if not isinstance(value, dict):
        return None, None
    lat = value.get("lat")
    lon = value.get("lon")
    if lat is None or lon is None:
        return None, None
    return float(lat), float(lon)
