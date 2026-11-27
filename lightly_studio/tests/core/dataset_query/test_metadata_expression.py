"""Tests for metadata comparisons in dataset queries."""

from __future__ import annotations

import operator
from collections.abc import Sequence
from typing import Any, cast

import pytest
from sqlalchemy.dialects import postgresql
from sqlmodel import Session, select

from lightly_studio.core.dataset_query.dataset_query import DatasetQuery
from lightly_studio.core.dataset_query.image_sample_field import ImageSampleField
from lightly_studio.core.dataset_query.match_expression import MatchExpression
from lightly_studio.core.image.image_sample import ImageSample
from lightly_studio.models.collection import CollectionTable
from lightly_studio.models.sample import SampleTable
from tests.helpers_resolvers import create_collection, create_image_with_metadata


class TestMetadataField:
    @pytest.mark.parametrize("threshold", [2, 2.0])
    @pytest.mark.parametrize(
        ("compare", "expected_indices"),
        [
            (operator.eq, [1, 2]),
            (operator.ne, [0, 3]),
            (operator.lt, [0]),
            (operator.le, [0, 1, 2]),
            (operator.gt, [3]),
            (operator.ge, [1, 2, 3]),
        ],
    )
    def test_comparisons__numbers(
        self,
        db_session: Session,
        threshold: int | float,
        compare: Any,
        expected_indices: list[int],
    ) -> None:
        collection = create_collection(session=db_session)
        # Numeric strings, booleans, null, containers, and missing paths never match.
        metadata_values: list[dict[str, Any]] = [
            {"value": -1.5},
            {"value": 2},
            {"value": 2.0},
            {"value": 10},
            {"value": "2"},
            {"value": "invalid"},
            {"value": True},
            {"value": False},
            {"value": None},
            {"value": {}},
            {"value": []},
            {"other": 2},
            {},
        ]
        images = [
            create_image_with_metadata(
                session=db_session,
                collection_id=collection.collection_id,
                file_path_abs=f"/image{index}.jpg",
                metadata=metadata,
            )
            for index, metadata in enumerate(metadata_values)
        ]
        _assert_matching_ids(
            session=db_session,
            collection=collection,
            expression=compare(ImageSampleField.metadata["value"], threshold),
            expected_samples=[images[index] for index in expected_indices],
        )

    @pytest.mark.parametrize(
        ("lower", "upper"),
        [(16777216, 16777217), (1.0000000000000002, 1.0000000000000004)],
    )
    @pytest.mark.parametrize(
        ("compare", "expected_indices"),
        [
            (operator.eq, [0]),
            (operator.ne, [1]),
            (operator.lt, []),
            (operator.le, [0]),
            (operator.gt, [1]),
            (operator.ge, [0, 1]),
        ],
    )
    def test_comparisons__numeric_precision(
        self,
        db_session: Session,
        lower: int | float,
        upper: int | float,
        compare: Any,
        expected_indices: list[int],
    ) -> None:
        collection = create_collection(session=db_session)
        images = [
            create_image_with_metadata(
                session=db_session,
                collection_id=collection.collection_id,
                file_path_abs=f"/image{index}.jpg",
                metadata={"value": value},
            )
            for index, value in enumerate([lower, upper])
        ]
        _assert_matching_ids(
            session=db_session,
            collection=collection,
            expression=compare(ImageSampleField.metadata["value"], lower),
            expected_samples=[images[index] for index in expected_indices],
        )

    @pytest.mark.parametrize("path", ["odometry.speed", "odometry.acc[1]", "odometry.acc[-1]"])
    def test_comparisons__nested_numbers(self, db_session: Session, path: str) -> None:
        collection = create_collection(session=db_session)
        image = create_image_with_metadata(
            session=db_session,
            collection_id=collection.collection_id,
            metadata={"odometry": {"speed": 2.5, "acc": [100, 2.5]}},
        )
        _assert_matching_ids(
            session=db_session,
            collection=collection,
            expression=ImageSampleField.metadata[path] < 3,
            expected_samples=[image],
        )

    @pytest.mark.parametrize("compare", [operator.lt, operator.le, operator.gt, operator.ge])
    @pytest.mark.parametrize("value", [True, False, "2", None, [], {}])
    def test_ordering__unsupported_value(self, compare: Any, value: Any) -> None:
        with pytest.raises(TypeError, match="require a"):
            compare(ImageSampleField.metadata["score"], value)

    @pytest.mark.parametrize(
        "compare", [operator.eq, operator.ne, operator.lt, operator.le, operator.gt, operator.ge]
    )
    def test_comparisons__nan(self, compare: Any) -> None:
        with pytest.raises(ValueError, match="do not support NaN"):
            compare(ImageSampleField.metadata["score"], float("nan"))

    def test_eq_ne__strings(self, db_session: Session) -> None:
        collection = create_collection(session=db_session)
        images = [
            create_image_with_metadata(
                session=db_session,
                collection_id=collection.collection_id,
                file_path_abs=f"/image{index}.jpg",
                metadata={"camera": value},
            )
            for index, value in enumerate(["front", "rear", None])
        ]
        field = ImageSampleField.metadata["camera"]
        _assert_matching_ids(
            session=db_session,
            collection=collection,
            expression=field == "front",
            expected_samples=[images[0]],
        )
        _assert_matching_ids(
            session=db_session,
            collection=collection,
            expression=field != "front",
            expected_samples=[images[1]],
        )

    def test_eq_ne__booleans(self, db_session: Session) -> None:
        collection = create_collection(session=db_session)
        images = [
            create_image_with_metadata(
                session=db_session,
                collection_id=collection.collection_id,
                file_path_abs=f"/image{index}.jpg",
                metadata={"reviewed": value},
            )
            for index, value in enumerate([True, False, "true"])
        ]
        field = ImageSampleField.metadata["reviewed"]
        _assert_matching_ids(
            session=db_session,
            collection=collection,
            expression=field == True,  # noqa: E712
            expected_samples=[images[0]],
        )
        _assert_matching_ids(
            session=db_session,
            collection=collection,
            expression=field == False,  # noqa: E712
            expected_samples=[images[1]],
        )
        _assert_matching_ids(
            session=db_session,
            collection=collection,
            expression=field != True,  # noqa: E712
            expected_samples=[images[1]],
        )
        _assert_matching_ids(
            session=db_session,
            collection=collection,
            expression=field == "true",
            expected_samples=[images[2]],
        )

    def test_eq_ne__nested_paths(self, db_session: Session) -> None:
        collection = create_collection(session=db_session)
        image = create_image_with_metadata(
            session=db_session,
            collection_id=collection.collection_id,
            metadata={"odometry": {"camera": "front", "cameras": ["front", "rear"]}},
        )
        _assert_matching_ids(
            session=db_session,
            collection=collection,
            expression=ImageSampleField.metadata["odometry.camera"] == "front",
            expected_samples=[image],
        )
        _assert_matching_ids(
            session=db_session,
            collection=collection,
            expression=ImageSampleField.metadata["odometry.cameras[0]"] == "front",
            expected_samples=[image],
        )
        _assert_matching_ids(
            session=db_session,
            collection=collection,
            expression=ImageSampleField.metadata["odometry.cameras[-1]"] != "front",
            expected_samples=[image],
        )

    def test_eq__special_characters(self, db_session: Session) -> None:
        collection = create_collection(session=db_session)
        image = create_image_with_metadata(
            session=db_session,
            collection_id=collection.collection_id,
            metadata={"camera's name": "O'Brien"},
        )
        _assert_matching_ids(
            session=db_session,
            collection=collection,
            expression=ImageSampleField.metadata["camera's name"] == "O'Brien",
            expected_samples=[image],
        )

    def test_eq_ne__non_scalar_numeric_and_missing_values(self, db_session: Session) -> None:
        collection = create_collection(session=db_session)
        # The last image has no metadata row. The preceding one has a missing path.
        metadata_values: list[dict[str, Any]] = [
            {"value": {}},
            {"value": []},
            {"value": 7},
            {"other": True},
            {},
        ]
        for index, metadata in enumerate(metadata_values):
            create_image_with_metadata(
                session=db_session,
                collection_id=collection.collection_id,
                file_path_abs=f"/image{index}.jpg",
                metadata=metadata,
            )
        field = ImageSampleField.metadata["value"]
        _assert_matching_ids(
            session=db_session,
            collection=collection,
            expression=field == "{}",
            expected_samples=[],
        )
        _assert_matching_ids(
            session=db_session,
            collection=collection,
            expression=field == "[]",
            expected_samples=[],
        )
        _assert_matching_ids(
            session=db_session,
            collection=collection,
            expression=field == "7",
            expected_samples=[],
        )
        _assert_matching_ids(
            session=db_session,
            collection=collection,
            expression=field != "front",
            expected_samples=[],
        )
        _assert_matching_ids(
            session=db_session,
            collection=collection,
            expression=field == True,  # noqa: E712
            expected_samples=[],
        )
        _assert_matching_ids(
            session=db_session,
            collection=collection,
            expression=field != True,  # noqa: E712
            expected_samples=[],
        )

    def test_eq__unsupported_value(self) -> None:
        with pytest.raises(TypeError, match="require a string, boolean, or number"):
            _ = ImageSampleField.metadata["score"] == cast(Any, None)
        with pytest.raises(TypeError, match="require a string, boolean, or number"):
            _ = ImageSampleField.metadata["score"] == cast(Any, [])
        with pytest.raises(TypeError, match="require a string, boolean, or number"):
            _ = ImageSampleField.metadata["score"] == cast(Any, {})
        with pytest.raises(TypeError, match="require a string, boolean, or number"):
            _ = ImageSampleField.metadata["score"] == cast(Any, object())


class TestMetadataComparisonExpression:
    def test_get__postgres_guards_numeric_cast(self) -> None:
        expression = ImageSampleField.metadata["odometry.acc[1]"] < 15
        query = select(SampleTable).where(expression.get())
        compiled = query.compile(dialect=postgresql.dialect())  # type: ignore[no-untyped-call]
        sql = str(compiled).lower()
        assert "then cast(" in sql
        assert "as double precision) end <" in sql
        assert {"odometry", "acc", 1, 15, "number"}.issubset(set(compiled.params.values()))

    def test_get__postgres_binds_nested_path(self) -> None:
        expression = ImageSampleField.metadata["odometry.camera"] == "front"
        query = select(SampleTable).where(expression.get())
        compiled = query.compile(dialect=postgresql.dialect())  # type: ignore[no-untyped-call]
        sql = str(compiled).lower()

        assert "exists (select 1" in sql
        assert "metadata.sample_id = sample.sample_id" in sql
        assert "->>" in sql
        assert {"odometry", "camera", "front"}.issubset(set(compiled.params.values()))


def _assert_matching_ids(
    session: Session,
    collection: CollectionTable,
    expression: MatchExpression,
    expected_samples: Sequence[ImageSample],
) -> None:
    """Assert that an expression matches the expected image samples."""
    query = DatasetQuery(dataset=collection, session=session)
    actual_ids = {sample.sample_id for sample in query.match(expression).to_list()}
    expected_ids = {sample.sample_id for sample in expected_samples}
    assert actual_ids == expected_ids
