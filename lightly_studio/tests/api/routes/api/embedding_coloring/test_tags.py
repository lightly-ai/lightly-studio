"""Tests for filter-aware tag coloring."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.api.routes.api.embedding_coloring import tags
from lightly_studio.resolvers import tag_resolver
from tests.helpers_resolvers import create_collection, create_image, create_tag


def test_build_tag_color_maps__hides_tag_without_matching_samples(
    db_session: Session,
) -> None:
    """A tag carried only by filtered-out samples drops from the legend."""
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    kept = create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/a.png"
    ).sample
    dropped = create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/b.png"
    ).sample

    kept_tag = create_tag(session=db_session, collection_id=collection_id, tag_name="kept")
    dropped_tag = create_tag(session=db_session, collection_id=collection_id, tag_name="dropped")
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session, tag_id=kept_tag.tag_id, sample_ids=[kept.sample_id]
    )
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session, tag_id=dropped_tag.tag_id, sample_ids=[dropped.sample_id]
    )

    _, legend = tags.build_tag_color_maps(
        session=db_session,
        tag_ids=[kept_tag.tag_id, dropped_tag.tag_id],
        sample_ids=[kept.sample_id, dropped.sample_id],
        matching_sample_ids={kept.sample_id},
    )

    assert sorted(legend.values()) == ["kept"]


def test_build_tag_color_maps__orders_by_in_filter_frequency(
    db_session: Session,
) -> None:
    """The tag on more matching samples gets the first color category."""
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    images = [
        create_image(
            session=db_session, collection_id=collection_id, file_path_abs=f"/img{i}.png"
        ).sample
        for i in range(3)
    ]

    rare = create_tag(session=db_session, collection_id=collection_id, tag_name="rare")
    common = create_tag(session=db_session, collection_id=collection_id, tag_name="common")
    # "rare" leads in insertion order but is carried by fewer matching samples.
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session, tag_id=rare.tag_id, sample_ids=[images[0].sample_id]
    )
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session,
        tag_id=common.tag_id,
        sample_ids=[images[0].sample_id, images[1].sample_id, images[2].sample_id],
    )

    _, legend = tags.build_tag_color_maps(
        session=db_session,
        tag_ids=[rare.tag_id, common.tag_id],
        sample_ids=[image.sample_id for image in images],
        matching_sample_ids=None,
    )

    # Frequency wins over insertion order: "common" takes the first slot.
    assert legend == {2: "common", 3: "rare"}
