"""Unit tests for tag-based embedding coloring."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.api.routes.api.embedding_coloring.tag import build_tag_color_maps
from lightly_studio.resolvers import tag_resolver
from tests.helpers_resolvers import create_collection, create_image, create_tag

START_CAT = 2


def test_single_tag(db_session: Session) -> None:
    """Members get start_cat, non-members get 1 (unassigned)."""
    collection = create_collection(session=db_session)
    cid = collection.collection_id

    img_a = create_image(session=db_session, collection_id=cid, file_path_abs="a.png")
    img_b = create_image(session=db_session, collection_id=cid, file_path_abs="b.png")

    tag = create_tag(session=db_session, collection_id=cid, tag_name="cats")
    tag_resolver.add_tag_to_sample(session=db_session, tag_id=tag.tag_id, sample=img_a.sample)

    sample_ids = [img_a.sample_id, img_b.sample_id]
    fulfils_filter = [1, 1]

    cats, legend = build_tag_color_maps(
        session=db_session,
        tag_ids=[tag.tag_id],
        sample_ids=sample_ids,
        fulfils_filter=fulfils_filter,
        start_cat=START_CAT,
    )

    assert cats == [2, 1]
    assert legend == {2: "cats"}


def test_multiple_tags_no_overlap(db_session: Session) -> None:
    """Each tag gets a consecutive category."""
    collection = create_collection(session=db_session)
    cid = collection.collection_id

    img_a = create_image(session=db_session, collection_id=cid, file_path_abs="a.png")
    img_b = create_image(session=db_session, collection_id=cid, file_path_abs="b.png")

    tag1 = create_tag(session=db_session, collection_id=cid, tag_name="dogs")
    tag2 = create_tag(session=db_session, collection_id=cid, tag_name="cats")
    tag_resolver.add_tag_to_sample(session=db_session, tag_id=tag1.tag_id, sample=img_a.sample)
    tag_resolver.add_tag_to_sample(session=db_session, tag_id=tag2.tag_id, sample=img_b.sample)

    sample_ids = [img_a.sample_id, img_b.sample_id]
    fulfils_filter = [1, 1]

    cats, legend = build_tag_color_maps(
        session=db_session,
        tag_ids=[tag1.tag_id, tag2.tag_id],
        sample_ids=sample_ids,
        fulfils_filter=fulfils_filter,
        start_cat=START_CAT,
    )

    assert cats == [2, 3]
    assert legend == {2: "dogs", 3: "cats"}


def test_overlapping_tags_first_match_wins(db_session: Session) -> None:
    """When a sample belongs to multiple tags, the first tag in tag_ids wins."""
    collection = create_collection(session=db_session)
    cid = collection.collection_id

    img = create_image(session=db_session, collection_id=cid, file_path_abs="a.png")

    tag1 = create_tag(session=db_session, collection_id=cid, tag_name="priority")
    tag2 = create_tag(session=db_session, collection_id=cid, tag_name="secondary")
    tag_resolver.add_tag_to_sample(session=db_session, tag_id=tag1.tag_id, sample=img.sample)
    tag_resolver.add_tag_to_sample(session=db_session, tag_id=tag2.tag_id, sample=img.sample)

    cats, legend = build_tag_color_maps(
        session=db_session,
        tag_ids=[tag1.tag_id, tag2.tag_id],
        sample_ids=[img.sample_id],
        fulfils_filter=[1],
        start_cat=START_CAT,
    )

    # tag1 is first → category 2 wins over category 3
    assert cats == [2]
    assert legend == {2: "priority", 3: "secondary"}


def test_filter_respected(db_session: Session) -> None:
    """Filtered-out samples (fulfils_filter==0) get category 0."""
    collection = create_collection(session=db_session)
    cid = collection.collection_id

    img = create_image(session=db_session, collection_id=cid, file_path_abs="a.png")
    tag = create_tag(session=db_session, collection_id=cid, tag_name="tagged")
    tag_resolver.add_tag_to_sample(session=db_session, tag_id=tag.tag_id, sample=img.sample)

    cats, _ = build_tag_color_maps(
        session=db_session,
        tag_ids=[tag.tag_id],
        sample_ids=[img.sample_id],
        fulfils_filter=[0],
        start_cat=START_CAT,
    )

    assert cats == [0]


def test_empty_tag_ids(db_session: Session) -> None:
    """With no tags requested, all samples get category 1 (unassigned)."""
    collection = create_collection(session=db_session)
    cid = collection.collection_id

    img = create_image(session=db_session, collection_id=cid, file_path_abs="a.png")

    cats, legend = build_tag_color_maps(
        session=db_session,
        tag_ids=[],
        sample_ids=[img.sample_id],
        fulfils_filter=[1],
        start_cat=START_CAT,
    )

    assert cats == [1]
    assert legend == {}


def test_tag_with_no_samples(db_session: Session) -> None:
    """A tag with no assigned samples still appears in the legend."""
    collection = create_collection(session=db_session)
    cid = collection.collection_id

    img = create_image(session=db_session, collection_id=cid, file_path_abs="a.png")
    tag = create_tag(session=db_session, collection_id=cid, tag_name="empty_tag")

    cats, legend = build_tag_color_maps(
        session=db_session,
        tag_ids=[tag.tag_id],
        sample_ids=[img.sample_id],
        fulfils_filter=[1],
        start_cat=START_CAT,
    )

    assert cats == [1]  # sample not in tag → unassigned
    assert legend == {2: "empty_tag"}
