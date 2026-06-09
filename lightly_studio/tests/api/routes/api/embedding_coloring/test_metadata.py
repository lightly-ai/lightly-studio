"""Tests for filter-aware metadata coloring."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.api.routes.api.embedding_coloring import metadata
from tests.helpers_resolvers import create_collection, create_image


def test_build_metadata_color_maps__hides_categories_absent_after_filtering(
    db_session: Session,
) -> None:
    """A value carried only by filtered-out samples drops from the legend."""
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    kept = create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/a.png"
    ).sample
    dropped = create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/b.png"
    ).sample
    kept["city"] = "Berlin"
    dropped["city"] = "Paris"

    _, legend = metadata.build_metadata_color_maps(
        session=db_session,
        collection_id=collection_id,
        key="city",
        sample_ids=[kept.sample_id, dropped.sample_id],
        matching_sample_ids={kept.sample_id},
    )

    # Only the value present among matching samples survives in the legend.
    assert sorted(legend.values()) == ["Berlin"]


def test_build_metadata_color_maps__filter_promotes_value_out_of_other(
    db_session: Session,
) -> None:
    """A value buried in "Other" globally gets its own slot once filtered to."""
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    # More distinct values than fit in the 254 individual slots, one per sample.
    samples = []
    for i in range(300):
        sample = create_image(
            session=db_session, collection_id=collection_id, file_path_abs=f"/img{i:03d}.png"
        ).sample
        sample["label"] = f"v{i:03d}"
        samples.append(sample)
    all_ids = [sample.sample_id for sample in samples]

    # Unfiltered: every value has frequency 1, so ordering is alphabetical and
    # the alphabetically-late values collapse into the trailing "Other" slot.
    _, legend_all = metadata.build_metadata_color_maps(
        session=db_session,
        collection_id=collection_id,
        key="label",
        sample_ids=all_ids,
        matching_sample_ids=None,
    )
    assert any(label.startswith("Other") for label in legend_all.values())
    assert "v299" not in legend_all.values()

    # Filter to the single sample whose value was inside "Other": it now is the
    # only value present, so it gets its own individual slot.
    _, legend_filtered = metadata.build_metadata_color_maps(
        session=db_session,
        collection_id=collection_id,
        key="label",
        sample_ids=all_ids,
        matching_sample_ids={samples[299].sample_id},
    )
    assert legend_filtered == {2: "v299"}


def test_build_metadata_color_maps__boolean_orders_by_frequency(
    db_session: Session,
) -> None:
    """Boolean values rank by in-filter frequency and drop when absent."""
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    true_sample = create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/t.png"
    ).sample
    false_sample = create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/f.png"
    ).sample
    true_sample["flag"] = True
    false_sample["flag"] = False

    _, legend = metadata.build_metadata_color_maps(
        session=db_session,
        collection_id=collection_id,
        key="flag",
        sample_ids=[true_sample.sample_id, false_sample.sample_id],
        matching_sample_ids={true_sample.sample_id},
    )

    # Only the matching sample's boolean value appears.
    assert legend == {2: "true"}
