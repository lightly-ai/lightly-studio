"""Tests for the joint distribution of two metadata keys."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.models.metadata import MetadataJointAxisBucketView, SampleMetadataTable
from lightly_studio.models.range import FloatRange
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.metadata_resolver.metadata_filter import MetadataFilter
from lightly_studio.resolvers.metadata_resolver.sample import get_metadata_joint_distribution
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from lightly_studio.resolvers.video_resolver.video_filter import VideoFilter
from tests.helpers_resolvers import create_collection, create_image
from tests.resolvers.video.helpers import VideoStub, create_video


def test_get_metadata_joint_distribution__categorical_by_integer(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    for month, year in [
        ("April", 2025),
        ("April", 2025),
        ("April", 2026),
        ("March", 2025),
        ("March", 2027),
    ]:
        _create_image_with_metadata(
            db_session=db_session,
            collection_id=collection_id,
            metadata={"month": month, "year": year},
        )

    distribution = get_metadata_joint_distribution.get_metadata_joint_distribution(
        session=db_session, collection_id=collection_id, x_key="month", y_key="year"
    )

    assert distribution.x_axis.key == "month"
    assert distribution.x_axis.type == "string"
    assert distribution.x_axis.buckets == [
        MetadataJointAxisBucketView(kind="value", value="April"),
        MetadataJointAxisBucketView(kind="value", value="March"),
    ]
    # The year range 2025..2027 fits in the default 10 buckets: one bucket per year.
    assert distribution.y_axis.type == "integer"
    assert distribution.y_axis.buckets == [
        MetadataJointAxisBucketView(kind="range", min=2025, max=2025),
        MetadataJointAxisBucketView(kind="range", min=2026, max=2026),
        MetadataJointAxisBucketView(kind="range", min=2027, max=2027),
    ]
    assert distribution.counts == [[2, 1], [1, 0], [0, 1]]


def test_get_metadata_joint_distribution__integer_buckets_wider_than_one(
    db_session: Session,
) -> None:
    collection_id = create_collection(session=db_session).collection_id
    for score in range(10):
        _create_image_with_metadata(
            db_session=db_session,
            collection_id=collection_id,
            metadata={"score": score, "group": "a"},
        )

    distribution = get_metadata_joint_distribution.get_metadata_joint_distribution(
        session=db_session,
        collection_id=collection_id,
        x_key="score",
        y_key="group",
        bin_count=4,
    )

    # The 10 values 0..9 need a width of 3 to fit in 4 buckets.
    assert distribution.x_axis.buckets == [
        MetadataJointAxisBucketView(kind="range", min=0, max=2),
        MetadataJointAxisBucketView(kind="range", min=3, max=5),
        MetadataJointAxisBucketView(kind="range", min=6, max=8),
        MetadataJointAxisBucketView(kind="range", min=9, max=9),
    ]
    assert distribution.counts == [[3, 3, 3, 1]]


def test_get_metadata_joint_distribution__float_bins(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    for brightness in [0.0, 0.5, 1.0]:
        _create_image_with_metadata(
            db_session=db_session,
            collection_id=collection_id,
            metadata={"brightness": brightness, "group": "a"},
        )

    distribution = get_metadata_joint_distribution.get_metadata_joint_distribution(
        session=db_session,
        collection_id=collection_id,
        x_key="brightness",
        y_key="group",
        bin_count=2,
    )

    assert distribution.x_axis.buckets == [
        MetadataJointAxisBucketView(kind="range", min=0.0, max=0.5),
        MetadataJointAxisBucketView(kind="range", min=0.5, max=1.0),
    ]
    # 0.5 opens the second bucket, and the max value 1.0 is in the last bucket.
    assert distribution.counts == [[1, 2]]


def test_get_metadata_joint_distribution__degenerate_float_axis(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    for group in ["a", "a", "b"]:
        _create_image_with_metadata(
            db_session=db_session,
            collection_id=collection_id,
            metadata={"brightness": 2.5, "group": group},
        )

    distribution = get_metadata_joint_distribution.get_metadata_joint_distribution(
        session=db_session, collection_id=collection_id, x_key="brightness", y_key="group"
    )

    assert distribution.x_axis.buckets == [
        MetadataJointAxisBucketView(kind="range", min=2.5, max=2.5)
    ]
    assert distribution.counts == [[2], [1]]


def test_get_metadata_joint_distribution__other_and_missing_buckets(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    for metadata in [
        {"city": "Zurich", "weather": "sunny"},
        {"city": "Zurich", "weather": "sunny"},
        {"city": "Bern", "weather": "sunny"},
        {"weather": "sunny"},
    ]:
        _create_image_with_metadata(
            db_session=db_session, collection_id=collection_id, metadata=metadata
        )
    create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/path/to/no-metadata.png"
    )

    distribution = get_metadata_joint_distribution.get_metadata_joint_distribution(
        session=db_session,
        collection_id=collection_id,
        x_key="city",
        y_key="weather",
        limit=1,
    )

    assert distribution.x_axis.buckets == [
        MetadataJointAxisBucketView(kind="value", value="Zurich"),
        MetadataJointAxisBucketView(kind="other"),
        MetadataJointAxisBucketView(kind="missing"),
    ]
    # Every weather value is in the top 1, so the weather axis has no "other" bucket.
    assert distribution.y_axis.buckets == [
        MetadataJointAxisBucketView(kind="value", value="sunny"),
        MetadataJointAxisBucketView(kind="missing"),
    ]
    assert distribution.counts == [[2, 1, 1], [0, 0, 1]]


def test_get_metadata_joint_distribution__boolean_values(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    for active, city in [(True, "Zurich"), (False, "Zurich"), (True, "Bern")]:
        _create_image_with_metadata(
            db_session=db_session,
            collection_id=collection_id,
            metadata={"active": active, "city": city},
        )

    distribution = get_metadata_joint_distribution.get_metadata_joint_distribution(
        session=db_session, collection_id=collection_id, x_key="active", y_key="city"
    )

    assert [bucket.value for bucket in distribution.x_axis.buckets] == [True, False]
    assert all(isinstance(bucket.value, bool) for bucket in distribution.x_axis.buckets)
    assert [bucket.value for bucket in distribution.y_axis.buckets] == ["Zurich", "Bern"]
    assert distribution.counts == [[1, 1], [1, 0]]


def test_get_metadata_joint_distribution__axis_filters_excluded_other_filters_apply(
    db_session: Session,
) -> None:
    collection_id = create_collection(session=db_session).collection_id
    for month, year, weather in [
        ("April", 2025, "sunny"),
        ("April", 2026, "rainy"),
        ("March", 2025, "sunny"),
    ]:
        _create_image_with_metadata(
            db_session=db_session,
            collection_id=collection_id,
            metadata={"month": month, "year": year, "weather": weather},
        )

    distribution = get_metadata_joint_distribution.get_metadata_joint_distribution(
        session=db_session,
        collection_id=collection_id,
        x_key="month",
        y_key="year",
        filters=ImageFilter(
            sample_filter=SampleFilter(
                metadata_filters=[
                    MetadataFilter(key="month", op="==", value="March"),
                    MetadataFilter(key="year", op=">=", value=2026),
                    MetadataFilter(key="weather", op="==", value="sunny"),
                ]
            )
        ),
    )

    # The month and year filters are ignored. The weather filter removes April 2026,
    # but the year axis still spans the full collection.
    assert [bucket.value for bucket in distribution.x_axis.buckets] == ["April", "March"]
    assert [bucket.min for bucket in distribution.y_axis.buckets] == [2025, 2026]
    assert distribution.counts == [[1, 1], [0, 0]]


def test_get_metadata_joint_distribution__video_filter(db_session: Session) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    for index, month in enumerate(["April", "March", "April", "March"]):
        video = create_video(
            session=db_session,
            collection_id=collection.collection_id,
            video=VideoStub(path=f"/path/to/video{index}.mp4", duration_s=float(index + 1)),
        )
        video.sample["month"] = month
        video.sample["year"] = 2025

    distribution = get_metadata_joint_distribution.get_metadata_joint_distribution(
        session=db_session,
        collection_id=collection.collection_id,
        x_key="month",
        y_key="year",
        filters=VideoFilter(duration_s=FloatRange(min=3.0, max=4.0)),
    )

    # Only the videos with a duration of 3 s and 4 s remain.
    assert [bucket.value for bucket in distribution.x_axis.buckets] == ["April", "March"]
    assert distribution.counts == [[1, 1]]


@pytest.mark.parametrize(
    ("x_key", "y_key", "match"),
    [
        ("city", "city", "different metadata keys"),
        ("city", "unknown", "Unknown metadata key 'unknown'"),
        ("city", "tags", "Metadata key 'tags' of type 'list' has no distribution"),
    ],
)
def test_get_metadata_joint_distribution__invalid_keys(
    db_session: Session, x_key: str, y_key: str, match: str
) -> None:
    collection_id = create_collection(session=db_session).collection_id
    _create_image_with_metadata(
        db_session=db_session,
        collection_id=collection_id,
        metadata={"city": "Zurich", "tags": ["a", "b"]},
    )

    with pytest.raises(ValueError, match=match):
        get_metadata_joint_distribution.get_metadata_joint_distribution(
            session=db_session, collection_id=collection_id, x_key=x_key, y_key=y_key
        )


def test_get_metadata_joint_distribution__numeric_key_without_values(
    db_session: Session,
) -> None:
    collection_id = create_collection(session=db_session).collection_id
    image = create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/path/to/null.png"
    )
    db_session.add(
        SampleMetadataTable(
            sample_id=image.sample_id,
            data={"score": None, "city": "Zurich"},
            metadata_schema={"score": "integer", "city": "string"},
        )
    )
    db_session.commit()

    with pytest.raises(ValueError, match="Metadata key 'score' has no values"):
        get_metadata_joint_distribution.get_metadata_joint_distribution(
            session=db_session, collection_id=collection_id, x_key="score", y_key="city"
        )


def _create_image_with_metadata(
    db_session: Session,
    collection_id: UUID,
    metadata: dict[str, Any],
) -> None:
    image = create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs=f"/path/to/{uuid4()}.png",
    )
    for key, value in metadata.items():
        image.sample[key] = value
