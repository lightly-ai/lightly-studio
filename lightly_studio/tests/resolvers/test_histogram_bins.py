import pytest
from sqlalchemy import literal, select
from sqlmodel import Session

from lightly_studio.resolvers import histogram_bins


@pytest.mark.parametrize(
    ("value", "expected_bucket"),
    [
        (0.0, 0),
        (2.4, 0),
        (2.5, 1),
        (9.9, 3),
        (10.0, 3),
        (-1.0, 0),
        (11.0, 3),
    ],
)
def test_bucket_expression(db_session: Session, value: float, expected_bucket: int) -> None:
    bucket = histogram_bins.bucket_expression(
        value=literal(value), min_value=0.0, max_value=10.0, bin_count=4
    )

    assert db_session.execute(select(bucket)).scalar_one() == expected_bucket


def test_bin_edges() -> None:
    assert histogram_bins.bin_edges(min_value=0.0, max_value=10.0, bin_count=4) == [
        0.0,
        2.5,
        5.0,
        7.5,
        10.0,
    ]


def test_bin_edges__last_edge_is_max() -> None:
    edges = histogram_bins.bin_edges(min_value=0.1, max_value=0.7, bin_count=3)

    assert edges[-1] == 0.7
