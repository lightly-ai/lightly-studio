"""Tests for the nearest-neighbor distance distribution resolver."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.resolvers.metadata_resolver.sample.get_nn_distance_distribution import (
    NN_DISTANCE_KEY,
    get_nn_distance_distributions,
)
from tests.helpers_resolvers import (
    ImageStub,
    create_collection,
    create_embedding_model,
    create_samples_with_embeddings,
)

# Four embeddings: sample0 and sample1 sit close together on the x-axis, while
# sample2 and sample3 are far away on other axes. So sample0/sample1 have a very
# small nearest-neighbor distance (0.1) and sample2/sample3 a large one (~1.35).
_IMAGES_AND_EMBEDDINGS = [
    (ImageStub(path="img0.jpg"), [1.0, 0.0, 0.0]),
    (ImageStub(path="img1.jpg"), [0.9, 0.0, 0.0]),
    (ImageStub(path="img2.jpg"), [0.0, 1.0, 0.0]),
    (ImageStub(path="img3.jpg"), [0.0, 0.0, 1.0]),
]


def _collection_with_embeddings(session: Session) -> tuple[UUID, list[UUID]]:
    collection_id = create_collection(session=session).collection_id
    embedding_model = create_embedding_model(
        session=session,
        collection_id=collection_id,
        embedding_model_name="example_embedding_model",
    )
    samples = create_samples_with_embeddings(
        session=session,
        collection_id=collection_id,
        embedding_model_id=embedding_model.embedding_model_id,
        images_and_embeddings=_IMAGES_AND_EMBEDDINGS,
    )
    return collection_id, [sample.sample_id for sample in samples]


def test_whole_collection_series__excludes_self_matches(db_session: Session) -> None:
    collection_id, _ = _collection_with_embeddings(db_session)

    [result] = get_nn_distance_distributions(
        session=db_session, collection_id=collection_id, scopes=[None], bins=10
    )

    assert result.key == NN_DISTANCE_KEY
    assert result.kind == "numeric"
    assert result.type == "float"
    assert result.bin_edges is not None
    assert len(result.bin_edges) == 11  # bins + 1 edges
    assert result.counts is not None
    assert sum(result.counts) == 4  # one value per embedded sample
    assert result.none_count == 0
    # Self-matches are excluded: had they been included every distance would be 0.0
    # and the range would collapse. Instead values span ~0.1 (close pair) to ~1.35.
    assert result.bin_edges[0] < 0.5 < result.bin_edges[-1]


def test_empty_scopes__returns_empty_list(db_session: Session) -> None:
    collection_id, _ = _collection_with_embeddings(db_session)

    assert (
        get_nn_distance_distributions(
            session=db_session, collection_id=collection_id, scopes=[]
        )
        == []
    )


def test_no_embedding_model__returns_empty_views(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id

    results = get_nn_distance_distributions(
        session=db_session, collection_id=collection_id, scopes=[None, {UUID(int=0)}]
    )

    assert len(results) == 2
    for result in results:
        assert result.kind == "numeric"
        assert result.bin_edges == []
        assert result.counts == []
    assert results[1].none_count == 1  # the scoped series counts its lone sample as none


def test_collection_with_fewer_than_two_embeddings__returns_empty_view(
    db_session: Session,
) -> None:
    collection_id = create_collection(session=db_session).collection_id
    embedding_model = create_embedding_model(
        session=db_session,
        collection_id=collection_id,
        embedding_model_name="example_embedding_model",
    )
    create_samples_with_embeddings(
        session=db_session,
        collection_id=collection_id,
        embedding_model_id=embedding_model.embedding_model_id,
        images_and_embeddings=_IMAGES_AND_EMBEDDINGS[:1],
    )

    [result] = get_nn_distance_distributions(
        session=db_session, collection_id=collection_id, scopes=[None]
    )

    # A single embedding has no neighbor anywhere, so no distance can be computed;
    # the lone sample is reported as having no value.
    assert result.bin_edges == []
    assert result.counts == []
    assert result.none_count == 1


def test_series_share_bin_edges_and_compute_within_scope(db_session: Session) -> None:
    collection_id, sample_ids = _collection_with_embeddings(db_session)

    # Two series: the whole collection, and the two orthogonal unit vectors. Their
    # nearest neighbor is searched *within* the subset, so both distances are the
    # mutual sqrt(2) — larger than they would be against the full collection.
    whole, subset = get_nn_distance_distributions(
        session=db_session,
        collection_id=collection_id,
        scopes=[None, {sample_ids[2], sample_ids[3]}],
        bins=5,
    )

    # Both series render on the same x-axis (union of their values).
    assert whole.bin_edges == subset.bin_edges

    assert subset.counts is not None
    assert sum(subset.counts) == 2
    assert subset.none_count == 0
    # Within-scope distance for the orthogonal pair is sqrt(2); it lands in the last
    # bin of the shared axis (the whole-collection series reaches up to ~1.35).
    assert subset.counts[-1] == 2


def test_scope_counts_samples_without_embeddings_as_none(db_session: Session) -> None:
    collection_id, sample_ids = _collection_with_embeddings(db_session)
    missing_id = UUID(int=0)  # not an embedded sample in this collection

    [result] = get_nn_distance_distributions(
        session=db_session,
        collection_id=collection_id,
        scopes=[{sample_ids[0], sample_ids[1], missing_id}],
    )

    assert result.counts is not None
    assert sum(result.counts) == 2
    assert result.none_count == 1
