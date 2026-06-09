"""Tests for filter-aware annotation coloring."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.api.routes.api.embedding_coloring import annotations as annotation_coloring
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
)


def test_build_annotation_color_maps__hides_label_without_matching_samples(
    db_session: Session,
) -> None:
    """A label carried only by filtered-out samples drops from the legend."""
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    kept = create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/a.png"
    ).sample
    dropped = create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/b.png"
    ).sample

    cat = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="cat"
    )
    dog = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="dog"
    )
    create_annotation(
        session=db_session,
        collection_id=collection_id,
        sample_id=kept.sample_id,
        annotation_label_id=cat.annotation_label_id,
    )
    create_annotation(
        session=db_session,
        collection_id=collection_id,
        sample_id=dropped.sample_id,
        annotation_label_id=dog.annotation_label_id,
    )

    _, legend = annotation_coloring.build_annotation_color_maps(
        session=db_session,
        annotation_label_ids=[cat.annotation_label_id, dog.annotation_label_id],
        sample_ids=[kept.sample_id, dropped.sample_id],
        matching_sample_ids={kept.sample_id},
    )

    assert sorted(legend.values()) == ["cat"]


def test_build_annotation_color_maps__orders_by_in_filter_frequency(
    db_session: Session,
) -> None:
    """The label on more matching samples gets the first color category."""
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    images = [
        create_image(
            session=db_session, collection_id=collection_id, file_path_abs=f"/img{i}.png"
        ).sample
        for i in range(3)
    ]

    rare = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="rare"
    )
    common = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="common"
    )
    # "rare" leads in insertion order but is carried by fewer samples.
    create_annotation(
        session=db_session,
        collection_id=collection_id,
        sample_id=images[0].sample_id,
        annotation_label_id=rare.annotation_label_id,
    )
    for image in images:
        create_annotation(
            session=db_session,
            collection_id=collection_id,
            sample_id=image.sample_id,
            annotation_label_id=common.annotation_label_id,
        )

    _, legend = annotation_coloring.build_annotation_color_maps(
        session=db_session,
        annotation_label_ids=[rare.annotation_label_id, common.annotation_label_id],
        sample_ids=[image.sample_id for image in images],
        matching_sample_ids=None,
    )

    assert legend == {2: "common", 3: "rare"}
