from __future__ import annotations

import math
from collections.abc import Sequence
from uuid import UUID, uuid4

import pytest
from sqlmodel import Session, col, select

from lightly_studio.models.caption import CaptionCreate, CaptionTable
from lightly_studio.models.collection import CollectionTable, SampleType
from lightly_studio.models.sample_embedding import SampleEmbeddingTable
from lightly_studio.models.temporal_span import TemporalSpanTable
from lightly_studio.resolvers import caption_resolver, collection_resolver
from tests.helpers_resolvers import (
    create_collection,
    create_embedding_model,
    create_image,
    create_sample_embedding,
)


def test_create_many__returns_empty_when_no_captions(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    assert (
        caption_resolver.create_many(
            session=db_session, parent_collection_id=collection_id, captions=[]
        )
        == []
    )


def test_create_many(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    image_one = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/samples/sample_one.jpg",
    )
    image_two = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/samples/sample_two.jpg",
    )

    inputs = [
        CaptionCreate(
            parent_sample_id=image_one.sample_id,
            text="hello world",
        ),
        CaptionCreate(
            parent_sample_id=image_one.sample_id,
            text="another hello",
        ),
        CaptionCreate(
            parent_sample_id=image_two.sample_id,
            text="lorem ipsum dolor",
        ),
    ]

    created_ids = caption_resolver.create_many(
        session=db_session, parent_collection_id=collection.collection_id, captions=inputs
    )
    created = caption_resolver.get_by_ids(session=db_session, sample_ids=created_ids)

    assert len(created) == 3
    # Check first caption
    assert created[0].parent_sample.collection_id == collection.collection_id
    assert created[0].parent_sample_id == image_one.sample_id
    assert created[0].text == "hello world"

    # Check second caption
    assert created[1].parent_sample.collection_id == collection.collection_id
    assert created[1].parent_sample_id == image_one.sample_id
    assert created[1].text == "another hello"

    # Check third caption
    assert created[2].parent_sample.collection_id == collection.collection_id
    assert created[2].parent_sample_id == image_two.sample_id
    assert created[2].text == "lorem ipsum dolor"

    stored_captions = db_session.exec(select(CaptionTable)).all()
    assert len(stored_captions) == 3


def test_create_many__check_collection_ids(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id
    image = create_image(session=db_session, collection_id=collection_id)

    created_ids = caption_resolver.create_many(
        session=db_session,
        parent_collection_id=collection_id,
        captions=[
            CaptionCreate(
                parent_sample_id=image.sample_id,
                text="hello world",
            ),
        ],
    )
    created = caption_resolver.get_by_ids(session=db_session, sample_ids=created_ids)[0]

    expected_caption_collection_id = collection_resolver.get_or_create_child_collection(
        session=db_session, collection_id=collection_id, sample_type=SampleType.CAPTION
    )
    assert created.sample.collection_id == expected_caption_collection_id
    assert created.parent_sample.collection_id == collection_id


def test_create_many__relationships(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id
    image = create_image(session=db_session, collection_id=collection_id)

    created_ids = caption_resolver.create_many(
        session=db_session,
        parent_collection_id=collection_id,
        captions=[
            CaptionCreate(
                parent_sample_id=image.sample_id,
                text="hello world",
            ),
        ],
    )
    created = caption_resolver.get_by_ids(session=db_session, sample_ids=created_ids)[0]
    caption_sample = created.sample
    parent_sample = created.parent_sample

    # Caption relationships
    assert caption_sample.sample_id == created.sample_id
    assert parent_sample.sample_id == image.sample_id

    # Parent sample captions relationship
    assert len(parent_sample.captions) == 1
    assert parent_sample.captions[0].sample_id == created.sample_id

    # Caption's sample captions relationships
    assert caption_sample.captions == []


def test_get_by_id(db_session: Session) -> None:
    collection = create_collection(session=db_session)

    image_a = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/samples/a.jpg",
    )

    created_caption_ids = caption_resolver.create_many(
        session=db_session,
        parent_collection_id=collection.collection_id,
        captions=[
            CaptionCreate(
                parent_sample_id=image_a.sample_id,
                text="first caption",
            ),
            CaptionCreate(
                parent_sample_id=image_a.sample_id,
                text="second caption",
            ),
        ],
    )

    # Retrieve 0
    caption_retrieved = caption_resolver.get_by_ids(session=db_session, sample_ids=[])
    assert len(caption_retrieved) == 0

    # Retrieve 1
    caption_retrieved = caption_resolver.get_by_ids(
        session=db_session, sample_ids=[created_caption_ids[0]]
    )
    assert len(caption_retrieved) == 1
    assert caption_retrieved[0].sample_id == created_caption_ids[0]

    # Retrieve many
    caption_retrieved = caption_resolver.get_by_ids(
        session=db_session, sample_ids=[created_caption_ids[0], created_caption_ids[1]]
    )
    assert len(caption_retrieved) == 2
    assert caption_retrieved[0].sample_id == created_caption_ids[0]
    assert caption_retrieved[1].sample_id == created_caption_ids[1]


def test_update__text(db_session: Session) -> None:
    collection = create_collection(session=db_session)

    image_a = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/samples/a.jpg",
    )

    created_caption_ids = caption_resolver.create_many(
        session=db_session,
        parent_collection_id=collection.collection_id,
        captions=[
            CaptionCreate(
                parent_sample_id=image_a.sample_id,
                text="first caption",
            ),
        ],
    )

    # Update the text and double check it got updated
    caption_updated = caption_resolver.update(
        session=db_session, sample_id=created_caption_ids[0], text="Updated text"
    )
    assert caption_updated.text == "Updated text"
    caption_retrieved = caption_resolver.get_by_ids(
        session=db_session, sample_ids=[created_caption_ids[0]]
    )
    assert caption_retrieved[0].text == "Updated text"


def test_update__no_fields(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    created_ids = caption_resolver.create_many(
        session=db_session,
        parent_collection_id=collection.collection_id,
        captions=[CaptionCreate(parent_sample_id=image.sample_id, text="caption")],
    )

    with pytest.raises(ValueError, match="No updates provided for the caption"):
        caption_resolver.update(session=db_session, sample_id=created_ids[0])


def test_create_many__with_temporal_span(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)

    created_ids = caption_resolver.create_many(
        session=db_session,
        parent_collection_id=collection.collection_id,
        captions=[
            CaptionCreate(
                parent_sample_id=image.sample_id,
                text="with span",
                start_time_s=1.0,
                end_time_s=2.5,
            ),
            CaptionCreate(
                parent_sample_id=image.sample_id,
                text="without span",
            ),
        ],
    )
    created = caption_resolver.get_by_ids(session=db_session, sample_ids=created_ids)

    assert created[0].temporal_span_details is not None
    assert created[0].temporal_span_details.start_time_s == 1.0
    assert created[0].temporal_span_details.end_time_s == 2.5
    assert created[1].temporal_span_details is None


def test_create_many__invalid_temporal_span(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)

    with pytest.raises(ValueError, match="start_time_s must be less than end_time_s"):
        caption_resolver.create_many(
            session=db_session,
            parent_collection_id=collection.collection_id,
            captions=[
                CaptionCreate(
                    parent_sample_id=image.sample_id,
                    text="bad span",
                    start_time_s=2.0,
                    end_time_s=1.0,
                ),
            ],
        )

    with pytest.raises(ValueError, match="Both start_time_s and end_time_s must be provided"):
        caption_resolver.create_many(
            session=db_session,
            parent_collection_id=collection.collection_id,
            captions=[
                CaptionCreate(
                    parent_sample_id=image.sample_id,
                    text="partial span",
                    start_time_s=1.0,
                ),
            ],
        )


@pytest.mark.parametrize(
    ("start_time_s", "end_time_s"),
    [
        (math.nan, 1.0),
        (0.0, math.nan),
        (math.inf, 1.0),
        (0.0, math.inf),
        (-math.inf, 1.0),
        (0.0, -math.inf),
    ],
)
def test_create_many__non_finite_temporal_span(
    db_session: Session, start_time_s: float, end_time_s: float
) -> None:
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)

    with pytest.raises(ValueError, match="start_time_s and end_time_s must be finite"):
        caption_resolver.create_many(
            session=db_session,
            parent_collection_id=collection.collection_id,
            captions=[
                CaptionCreate(
                    parent_sample_id=image.sample_id,
                    text="non-finite span",
                    start_time_s=start_time_s,
                    end_time_s=end_time_s,
                ),
            ],
        )


def test_update__creates_temporal_span_when_missing(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    created_ids = caption_resolver.create_many(
        session=db_session,
        parent_collection_id=collection.collection_id,
        captions=[CaptionCreate(parent_sample_id=image.sample_id, text="caption")],
    )

    updated = caption_resolver.update(
        session=db_session, sample_id=created_ids[0], start_time_s=1.0, end_time_s=3.0
    )
    assert updated.temporal_span_details is not None
    assert updated.temporal_span_details.start_time_s == 1.0
    assert updated.temporal_span_details.end_time_s == 3.0


def test_update__text_and_temporal_span(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    created_ids = caption_resolver.create_many(
        session=db_session,
        parent_collection_id=collection.collection_id,
        captions=[CaptionCreate(parent_sample_id=image.sample_id, text="caption")],
    )

    updated = caption_resolver.update(
        session=db_session,
        sample_id=created_ids[0],
        text="new text",
        start_time_s=1.0,
        end_time_s=3.0,
    )
    assert updated.text == "new text"
    assert updated.temporal_span_details is not None
    assert updated.temporal_span_details.start_time_s == 1.0
    assert updated.temporal_span_details.end_time_s == 3.0


def test_update__invalid_temporal_span(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    created_ids = caption_resolver.create_many(
        session=db_session,
        parent_collection_id=collection.collection_id,
        captions=[CaptionCreate(parent_sample_id=image.sample_id, text="caption")],
    )

    with pytest.raises(ValueError, match="start_time_s must be less than end_time_s"):
        caption_resolver.update(
            session=db_session, sample_id=created_ids[0], start_time_s=5.0, end_time_s=1.0
        )

    with pytest.raises(ValueError, match="start_time_s and end_time_s must be finite"):
        caption_resolver.update(
            session=db_session, sample_id=created_ids[0], start_time_s=math.inf, end_time_s=1.0
        )

    with pytest.raises(ValueError, match="Both start_time_s and end_time_s must be provided"):
        caption_resolver.update(session=db_session, sample_id=created_ids[0], start_time_s=1.0)


def test_update__not_found(db_session: Session) -> None:
    wrong_id = uuid4()
    with pytest.raises(ValueError, match=f"Caption with ID {wrong_id} not found."):
        caption_resolver.update(
            session=db_session, sample_id=wrong_id, start_time_s=1.0, end_time_s=2.0
        )


def test_delete_caption(db_session: Session) -> None:
    collection = create_collection(session=db_session)

    image = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/samples/a.jpg",
    )

    caption_ids = caption_resolver.create_many(
        session=db_session,
        parent_collection_id=collection.collection_id,
        captions=[
            CaptionCreate(
                parent_sample_id=image.sample_id,
                text="first caption",
            ),
            CaptionCreate(
                parent_sample_id=image.sample_id,
                text="second caption",
            ),
        ],
    )

    # Assert that we have two captions
    assert len(image.sample.captions) == 2

    # Delete the first caption
    caption_resolver.delete_caption(session=db_session, sample_id=caption_ids[0])

    # Assert that only second caption is left
    assert len(image.sample.captions) == 1
    assert image.sample.captions[0].sample_id == caption_ids[1]

    # Try to delete a non-existing caption
    wrong_id = uuid4()
    with pytest.raises(ValueError, match=f"Caption with ID {wrong_id} not found."):
        caption_resolver.delete_caption(session=db_session, sample_id=wrong_id)


def test_delete_caption__removes_temporal_span(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)

    caption_ids = caption_resolver.create_many(
        session=db_session,
        parent_collection_id=collection.collection_id,
        captions=[
            CaptionCreate(
                parent_sample_id=image.sample_id,
                text="with span",
                start_time_s=1.0,
                end_time_s=2.5,
            ),
        ],
    )

    caption_resolver.delete_caption(session=db_session, sample_id=caption_ids[0])

    # The caption's temporal span must not be left orphaned.
    remaining_spans = db_session.exec(
        select(TemporalSpanTable).where(col(TemporalSpanTable.sample_id) == caption_ids[0])
    ).all()
    assert remaining_spans == []


def test_delete_caption__removes_embedding(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    _, caption_id, _ = _create_embedded_caption(session=db_session, collection=collection)

    caption_resolver.delete_caption(session=db_session, sample_id=caption_id)

    # The deleted caption's embedding must not be left orphaned.
    assert _get_embeddings(session=db_session, sample_id=caption_id) == []


def test_get_unembedded_captions(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)

    caption_ids = caption_resolver.create_many(
        session=db_session,
        parent_collection_id=collection.collection_id,
        captions=[
            CaptionCreate(parent_sample_id=image.sample_id, text="embedded caption"),
            CaptionCreate(parent_sample_id=image.sample_id, text="unembedded caption"),
            CaptionCreate(parent_sample_id=image.sample_id, text=""),
        ],
    )
    caption_collection_id = collection_resolver.get_or_create_child_collection(
        session=db_session,
        collection_id=collection.collection_id,
        sample_type=SampleType.CAPTION,
    )
    embedding_model = create_embedding_model(
        session=db_session, collection_id=caption_collection_id
    )
    create_sample_embedding(
        session=db_session,
        sample_id=caption_ids[0],
        embedding_model_id=embedding_model.embedding_model_id,
        embedding=[1.0, 2.0, 3.0],
    )

    unembedded = caption_resolver.get_unembedded_captions(
        session=db_session,
        caption_collection_id=caption_collection_id,
        embedding_model_id=embedding_model.embedding_model_id,
    )

    # The already embedded caption and the caption without text are both skipped.
    assert [caption.sample_id for caption in unembedded] == [caption_ids[1]]


def test_get_unembedded_captions__other_embedding_model(db_session: Session) -> None:
    """A caption embedded with another model still needs an embedding for this one."""
    collection = create_collection(session=db_session)
    caption_collection_id, caption_id, _ = _create_embedded_caption(
        session=db_session, collection=collection
    )

    unembedded = caption_resolver.get_unembedded_captions(
        session=db_session,
        caption_collection_id=caption_collection_id,
        embedding_model_id=uuid4(),
    )

    assert [caption.sample_id for caption in unembedded] == [caption_id]


def test_get_unembedded_captions__filters_by_sample_ids(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)

    caption_ids = caption_resolver.create_many(
        session=db_session,
        parent_collection_id=collection.collection_id,
        captions=[
            CaptionCreate(parent_sample_id=image.sample_id, text="first"),
            CaptionCreate(parent_sample_id=image.sample_id, text="second"),
        ],
    )
    caption_collection_id = collection_resolver.get_or_create_child_collection(
        session=db_session,
        collection_id=collection.collection_id,
        sample_type=SampleType.CAPTION,
    )

    unembedded = caption_resolver.get_unembedded_captions(
        session=db_session,
        caption_collection_id=caption_collection_id,
        embedding_model_id=uuid4(),
        sample_ids=[caption_ids[1]],
    )

    assert [caption.sample_id for caption in unembedded] == [caption_ids[1]]


def test_update__text_drops_stale_embedding(db_session: Session) -> None:
    """The stored embedding describes the old text, so it is dropped on a text change."""
    collection = create_collection(session=db_session)
    _, caption_id, _ = _create_embedded_caption(session=db_session, collection=collection)

    caption_resolver.update(session=db_session, sample_id=caption_id, text="updated caption")

    assert _get_embeddings(session=db_session, sample_id=caption_id) == []


def test_update__temporal_span_keeps_embedding(db_session: Session) -> None:
    """Moving a caption in time leaves its text, and therefore its embedding, valid."""
    collection = create_collection(session=db_session)
    _, caption_id, _ = _create_embedded_caption(session=db_session, collection=collection)

    caption_resolver.update(
        session=db_session, sample_id=caption_id, start_time_s=3.0, end_time_s=4.0
    )

    assert len(_get_embeddings(session=db_session, sample_id=caption_id)) == 1


def _create_embedded_caption(
    session: Session, collection: CollectionTable
) -> tuple[UUID, UUID, UUID]:
    """Create a single caption with a stored embedding.

    Returns:
        The caption collection ID, the caption sample ID and the embedding model ID.
    """
    image = create_image(session=session, collection_id=collection.collection_id)
    caption_ids = caption_resolver.create_many(
        session=session,
        parent_collection_id=collection.collection_id,
        captions=[
            CaptionCreate(
                parent_sample_id=image.sample_id,
                text="first caption",
                start_time_s=1.0,
                end_time_s=2.0,
            )
        ],
    )
    caption_collection_id = collection_resolver.get_or_create_child_collection(
        session=session,
        collection_id=collection.collection_id,
        sample_type=SampleType.CAPTION,
    )
    embedding_model = create_embedding_model(session=session, collection_id=caption_collection_id)
    create_sample_embedding(
        session=session,
        sample_id=caption_ids[0],
        embedding_model_id=embedding_model.embedding_model_id,
        embedding=[1.0, 2.0, 3.0],
    )
    return caption_collection_id, caption_ids[0], embedding_model.embedding_model_id


def _get_embeddings(session: Session, sample_id: UUID) -> Sequence[SampleEmbeddingTable]:
    """Return the stored embeddings of a sample, across all embedding models."""
    return session.exec(
        select(SampleEmbeddingTable).where(col(SampleEmbeddingTable.sample_id) == sample_id)
    ).all()
