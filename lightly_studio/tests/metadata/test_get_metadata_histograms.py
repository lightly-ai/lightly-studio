"""Test the filtered metadata histograms resolver."""

from uuid import UUID

import pytest
from sqlmodel import Session

from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.metadata_resolver.metadata_filter import MetadataFilter
from lightly_studio.resolvers.metadata_resolver.sample import get_metadata_info
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from tests.helpers_resolvers import create_collection, create_image


def _create_samples_with_scores(db_session: Session, collection_id: UUID) -> None:
    """Create 10 samples with score 0..9, parity flag even_score 0/1, and constant 5.0."""
    for i in range(10):
        sample = create_image(
            session=db_session,
            collection_id=collection_id,
            file_path_abs=f"/path/to/sample{i}.png",
        ).sample
        sample["score"] = float(i)
        sample["even_score"] = i % 2
        sample["constant"] = 5.0


def test_get_metadata_histograms__unfiltered_matches_totals(db_session: Session) -> None:
    """Without filters, every value lands in a bin and edges span min..max."""
    collection = create_collection(session=db_session)
    _create_samples_with_scores(db_session, collection.collection_id)

    histograms = get_metadata_info.get_metadata_histograms(
        session=db_session, collection_id=collection.collection_id
    )

    score = histograms["score"]
    assert len(score.bin_edges) == len(score.counts) + 1
    assert score.bin_edges[0] == pytest.approx(0.0)
    assert score.bin_edges[-1] == pytest.approx(9.0)
    assert sum(score.counts) == 10


def test_get_metadata_histograms__filter_reduces_counts_keeps_edges(
    db_session: Session,
) -> None:
    """Filtering on another key reduces counts but keeps the full-domain edges."""
    collection = create_collection(session=db_session)
    _create_samples_with_scores(db_session, collection.collection_id)

    filters = ImageFilter(
        sample_filter=SampleFilter(
            metadata_filters=[MetadataFilter(key="even_score", op="==", value=0)]
        )
    )
    histograms = get_metadata_info.get_metadata_histograms(
        session=db_session, collection_id=collection.collection_id, filters=filters
    )

    score = histograms["score"]
    # Edges still span the unfiltered domain.
    assert score.bin_edges[0] == pytest.approx(0.0)
    assert score.bin_edges[-1] == pytest.approx(9.0)
    # Only the 5 even scores remain.
    assert sum(score.counts) == 5


def test_get_metadata_histograms__own_key_filter_is_excluded(db_session: Session) -> None:
    """A key's own metadata filter does not restrict its histogram (faceting)."""
    collection = create_collection(session=db_session)
    _create_samples_with_scores(db_session, collection.collection_id)

    filters = ImageFilter(
        sample_filter=SampleFilter(
            metadata_filters=[
                MetadataFilter(key="score", op=">=", value=8),
                MetadataFilter(key="even_score", op="==", value=0),
            ]
        )
    )
    histograms = get_metadata_info.get_metadata_histograms(
        session=db_session, collection_id=collection.collection_id, filters=filters
    )

    # The score histogram ignores the score filter but applies the parity one.
    assert sum(histograms["score"].counts) == 5
    # The parity histogram ignores its own filter but applies the score one:
    # scores >= 8 leave two samples (8 even, 9 odd).
    assert sum(histograms["even_score"].counts) == 2


def test_get_metadata_histograms__constant_field_counts_filtered(
    db_session: Session,
) -> None:
    """A constant-valued key returns a single degenerate bin whose count respects filters."""
    collection = create_collection(session=db_session)
    _create_samples_with_scores(db_session, collection.collection_id)

    histograms = get_metadata_info.get_metadata_histograms(
        session=db_session,
        collection_id=collection.collection_id,
        filters=ImageFilter(
            sample_filter=SampleFilter(
                metadata_filters=[MetadataFilter(key="score", op="<=", value=3)]
            )
        ),
    )

    constant = histograms["constant"]
    # All values are equal, so the degenerate range collapses to a single bin.
    assert constant.bin_edges == pytest.approx([5.0, 5.0])
    # score <= 3 keeps 4 samples, all carrying the constant value.
    assert constant.counts == [4]


def test_get_metadata_histograms__custom_bin_count(db_session: Session) -> None:
    """The bin count is configurable; edges still span the full domain."""
    collection = create_collection(session=db_session)
    _create_samples_with_scores(db_session, collection.collection_id)

    histograms = get_metadata_info.get_metadata_histograms(
        session=db_session, collection_id=collection.collection_id, bin_count=5
    )

    score = histograms["score"]
    assert len(score.counts) == 5
    assert len(score.bin_edges) == 6
    assert score.bin_edges[0] == pytest.approx(0.0)
    assert score.bin_edges[-1] == pytest.approx(9.0)
    assert sum(score.counts) == 10


def test_get_metadata_histograms__skips_non_numeric_keys(db_session: Session) -> None:
    """String and boolean keys produce no histogram."""
    collection = create_collection(session=db_session)
    sample = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/path/to/sample.png",
    ).sample
    sample["location"] = "city"
    sample["score"] = 1.0

    histograms = get_metadata_info.get_metadata_histograms(
        session=db_session, collection_id=collection.collection_id
    )

    assert "location" not in histograms
    assert "score" in histograms
