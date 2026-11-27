"""Checks for overlapping tags and filter-based color ordering."""

import pytest
from sqlmodel import Session

from lightly_studio.api.routes.api.embedding_coloring import tags
from lightly_studio.models.sample import SampleTagLinkTable
from tests.helpers_resolvers import create_collection, create_image, create_tag


@pytest.mark.parametrize(
    ("filtered", "expected_colors", "expected_legend"),
    [
        (False, [[3, 4], [3]], {3: "alpha", 4: "beta"}),
        (True, [[3], [3]], {3: "alpha"}),
    ],
)
def test_build_tag_color_maps(
    db_session: Session,
    filtered: bool,
    expected_colors: list[list[int]],
    expected_legend: dict[int, str],
) -> None:
    collection = create_collection(session=db_session)
    first = create_image(session=db_session, collection_id=collection.collection_id)
    second = create_image(session=db_session, collection_id=collection.collection_id)
    alpha = create_tag(session=db_session, collection_id=collection.collection_id, tag_name="alpha")
    beta = create_tag(session=db_session, collection_id=collection.collection_id, tag_name="beta")
    db_session.add_all(
        [
            SampleTagLinkTable(sample_id=first.sample_id, tag_id=alpha.tag_id),
            SampleTagLinkTable(sample_id=second.sample_id, tag_id=alpha.tag_id),
            SampleTagLinkTable(sample_id=first.sample_id, tag_id=beta.tag_id),
        ]
    )
    db_session.commit()

    colors, legend = tags.build_tag_color_maps(
        session=db_session,
        tag_ids=[beta.tag_id, alpha.tag_id],
        sample_ids=[first.sample_id, second.sample_id],
        matching_sample_ids={second.sample_id} if filtered else None,
    )

    assert colors == expected_colors
    assert legend == expected_legend


def test_build_tag_color_maps__collection_scope(db_session: Session) -> None:
    """A foreign tag must not add categories absent from this collection's samples."""
    collection = create_collection(session=db_session)
    other = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    foreign_image = create_image(session=db_session, collection_id=other.collection_id)
    tag = create_tag(session=db_session, collection_id=other.collection_id, tag_name="foreign")
    db_session.add(SampleTagLinkTable(sample_id=foreign_image.sample_id, tag_id=tag.tag_id))
    db_session.commit()

    assert tags.build_tag_color_maps(
        session=db_session,
        tag_ids=[tag.tag_id],
        sample_ids=[image.sample_id],
        matching_sample_ids=None,
        collection_id=collection.collection_id,
    ) == ([[]], {})
