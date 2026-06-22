"""Test database sampling functions."""

from __future__ import annotations

import re
from uuid import UUID, uuid4

import numpy as np
import pytest
from pydantic import ValidationError
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.models.tag import TagCreate
from lightly_studio.resolvers import (
    image_resolver,
    tag_resolver,
)
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from lightly_studio.sampling.mundig import Mundig
from lightly_studio.sampling.sampling_config import (
    AnnotationClassBalancingStrategy,
    EmbeddingDeduplicationStrategy,
    EmbeddingDiversityStrategy,
    EmbeddingSimilarityStrategy,
    SamplingConfig,
    SamplingStrategy,
)
from lightly_studio.sampling.sampling_via_db import (
    _aggregate_class_distributions,
    sampling_via_database,
)
from tests.helpers_resolvers import (
    AnnotationDetails,
    create_annotation_label,
    create_annotations,
    create_tag,
    fill_db_with_samples_and_embeddings,
)


def test_sampling_via_database__embedding_diversity(
    db_session: Session,
) -> None:
    """Runs sampling with a simple embedding diversity strategy."""
    collection_id = fill_db_with_samples_and_embeddings(
        db_session, n_samples=20, embedding_model_names=["embedding_model_1"]
    )

    sampling_config = SamplingConfig(
        collection_id=collection_id,
        n_samples_to_select=2,
        sampling_result_tag_name="sampling_1",
        strategies=[EmbeddingDiversityStrategy(embedding_model_name="embedding_model_1")],
    )

    sampling_via_database(
        db_session, sampling_config, input_sample_ids=_all_sample_ids(db_session, collection_id)
    )

    # Assert that the tag for the sampled set was created with 2 samples
    tags = tag_resolver.get_all_by_collection_id(db_session, collection_id=collection_id)
    assert len(tags) == 1
    assert tags[0].name == "sampling_1"
    samples_in_tag = image_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection_id,
        filters=ImageFilter(sample_filter=SampleFilter(tag_ids=[tags[0].tag_id])),
    ).samples
    assert len(samples_in_tag) == 2

    # Assert that the samples in the tag are the expected ones:
    # The first sample and most distant one should be sampled.
    expected_sample_paths = {"sample_0.jpg", "sample_19.jpg"}
    actual_sample_paths = {sample.file_path_abs for sample in samples_in_tag}
    assert actual_sample_paths == expected_sample_paths


def test_sampling_via_database__embedding_deduplication(
    db_session: Session,
) -> None:
    """Runs sampling with an embedding deduplication strategy.

    The embeddings lie on a line at positions [i, i] for sample i, so the
    distance between two samples is sqrt(2) * |i - j|. With a stopping condition
    of 5.0, selection stops before reaching the requested number of samples,
    keeping only samples that are sufficiently distant from each other.
    """
    collection_id = fill_db_with_samples_and_embeddings(
        db_session, n_samples=20, embedding_model_names=["embedding_model_1"]
    )

    sampling_config = SamplingConfig(
        collection_id=collection_id,
        n_samples_to_select=10,
        sampling_result_tag_name="sampling_1",
        strategies=[
            EmbeddingDeduplicationStrategy(
                embedding_model_name="embedding_model_1",
                stopping_condition_minimum_distance=5.0,
            )
        ],
    )

    sampling_via_database(
        db_session, sampling_config, input_sample_ids=_all_sample_ids(db_session, collection_id)
    )

    tags = tag_resolver.get_all_by_collection_id(db_session, collection_id=collection_id)
    assert len(tags) == 1
    assert tags[0].name == "sampling_1"
    samples_in_tag = image_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection_id,
        filters=ImageFilter(sample_filter=SampleFilter(tag_ids=[tags[0].tag_id])),
    ).samples

    # The stopping condition halts selection before reaching the requested 10 samples.
    assert 2 <= len(samples_in_tag) < 10

    # Each selected sample i has embedding [i, i], so the distance between samples
    # i and j is sqrt(2) * |i - j|. Deduplication guarantees that all selected
    # samples stay at least the minimum distance (5.0) apart.
    selected_positions = [
        int(sample.file_path_abs.removeprefix("sample_").removesuffix(".jpg"))
        for sample in samples_in_tag
    ]
    for i in selected_positions:
        for j in selected_positions:
            if i != j:
                assert np.sqrt(2) * abs(i - j) >= 5.0


def test_embedding_deduplication_strategy__rejects_negative_minimum_distance() -> None:
    """The deduplication strategy rejects a negative minimum distance."""
    with pytest.raises(ValidationError):
        EmbeddingDeduplicationStrategy(stopping_condition_minimum_distance=-0.1)


def test_sampling_via_database__multi_embedding_diversity(
    db_session: Session,
) -> None:
    """Runs sampling with multiple embedding diversity strategies."""
    collection_id = fill_db_with_samples_and_embeddings(
        db_session,
        n_samples=20,
        embedding_model_names=["embedding_model_1", "embedding_model_2"],
    )

    sampling_config = SamplingConfig(
        collection_id=collection_id,
        n_samples_to_select=2,
        sampling_result_tag_name="sampling_1",
        strategies=[
            EmbeddingDiversityStrategy(embedding_model_name="embedding_model_1"),
            EmbeddingDiversityStrategy(embedding_model_name="embedding_model_2"),
        ],
    )
    sampling_via_database(
        db_session, sampling_config, input_sample_ids=_all_sample_ids(db_session, collection_id)
    )

    # Assert that the tag for the sampled set was created with 2 samples
    tags = tag_resolver.get_all_by_collection_id(db_session, collection_id=collection_id)
    assert len(tags) == 1
    assert tags[0].name == "sampling_1"
    samples_in_tag = image_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection_id,
        filters=ImageFilter(sample_filter=SampleFilter(tag_ids=[tags[0].tag_id])),
    ).samples

    # Assert that the samples in the tag are the expected ones:
    # The first sample and most distant one should be sampled.
    expected_sample_paths = {"sample_0.jpg", "sample_19.jpg"}
    actual_sample_paths = {sample.file_path_abs for sample in samples_in_tag}
    assert actual_sample_paths == expected_sample_paths


def test_sampling_via_database__embedding_diversity__sample_filter_tags(
    db_session: Session,
) -> None:
    """Runs sampling with a filter for the input tag."""
    collection_id = fill_db_with_samples_and_embeddings(
        db_session, n_samples=101, embedding_model_names=["embedding_model_1"]
    )

    # Create a tag and add some samples to it
    tag = tag_resolver.create(
        session=db_session,
        tag=TagCreate(
            collection_id=collection_id,
            name="samples_5_through_14",
            kind="sample",
            description="A test tag",
        ),
    )
    all_samples = image_resolver.get_all_by_collection_id(
        session=db_session, pagination=None, collection_id=collection_id
    ).samples
    assert len(all_samples) == 101
    samples_5_through_14 = sorted(all_samples, key=lambda s: s.created_at)[5:15]
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session,
        tag_id=tag.tag_id,
        sample_ids=[s.sample_id for s in samples_5_through_14],
    )

    # Run diversity sampling with the tag as input
    sampling_config = SamplingConfig(
        collection_id=collection_id,
        n_samples_to_select=2,
        sampling_result_tag_name="sampling_1",
        strategies=[EmbeddingDiversityStrategy(embedding_model_name="embedding_model_1")],
    )
    sampling_via_database(
        db_session,
        sampling_config,
        input_sample_ids=[s.sample_id for s in samples_5_through_14],
    )

    # Assert that the tag for the sampled set was created with 2 samples
    tags = tag_resolver.get_all_by_collection_id(db_session, collection_id=collection_id)
    assert len(tags) == 2
    tag_sampled = next(
        t for t in tags if t.name == "sampling_1"
    )  # Get the tag created by the sampling
    samples_in_tag = image_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection_id,
        filters=ImageFilter(sample_filter=SampleFilter(tag_ids=[tag_sampled.tag_id])),
    ).samples
    assert len(samples_in_tag) == 2

    # Assert that the samples in the tag are the expected ones:
    # The first sample and most distant one should be sampled.
    expected_sample_paths = {"sample_5.jpg", "sample_14.jpg"}
    actual_sample_paths = {sample.file_path_abs for sample in samples_in_tag}
    assert actual_sample_paths == expected_sample_paths


def test_sampling_via_database__embedding_similarity(
    db_session: Session,
) -> None:
    """Runs sampling with an embedding similarity strategy."""
    collection_id = fill_db_with_samples_and_embeddings(
        db_session, n_samples=5, embedding_model_names=["embedding_model_1"]
    )
    all_samples = image_resolver.get_all_by_collection_id(
        session=db_session, pagination=None, collection_id=collection_id
    ).samples
    query_tag = create_tag(session=db_session, collection_id=collection_id, tag_name="query_tag")
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session,
        tag_id=query_tag.tag_id,
        sample_ids=[all_samples[0].sample_id, all_samples[1].sample_id],
    )

    sampling_config = SamplingConfig(
        collection_id=collection_id,
        n_samples_to_select=2,
        sampling_result_tag_name="sampling_1",
        strategies=[
            EmbeddingSimilarityStrategy(
                query_tag_name="query_tag",
                embedding_model_name="embedding_model_1",
            )
        ],
    )

    sampling_via_database(
        db_session, sampling_config, input_sample_ids=_all_sample_ids(db_session, collection_id)
    )

    tags = tag_resolver.get_all_by_collection_id(db_session, collection_id=collection_id)
    assert len(tags) == 2

    sampling_tag = next(tag for tag in tags if tag.name == "sampling_1")
    samples_in_tag = image_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection_id,
        filters=ImageFilter(sample_filter=SampleFilter(tag_ids=[sampling_tag.tag_id])),
    ).samples

    # Similarity returns the 2 samples that we compared against. Those are the most similar samples
    # from the dataset.
    expected_sample_paths = {"sample_0.jpg", "sample_1.jpg"}
    actual_sample_paths = {sample.file_path_abs for sample in samples_in_tag}
    assert actual_sample_paths == expected_sample_paths


def test_sampling_via_database__unknown_strategy(
    db_session: Session,
) -> None:
    """Runs sampling with a non-existing strategy.

    Check for the correct error message.
    """
    collection_id = fill_db_with_samples_and_embeddings(
        db_session, n_samples=20, embedding_model_names=["embedding_model_1"]
    )

    sampling_config = SamplingConfig(
        collection_id=collection_id,
        n_samples_to_select=2,
        sampling_result_tag_name="sampling_1",
        strategies=[SamplingStrategy()],
    )

    expected_error = "Sampling strategy of type <class "
    "'lightly_studio.sampling.sampling_config.SamplingStrategy'> is unknown."
    with pytest.raises(
        ValueError,
        match=expected_error,
    ):
        sampling_via_database(
            db_session,
            sampling_config,
            input_sample_ids=_all_sample_ids(db_session, collection_id),
        )


def test_sampling_via_database__embedding_similarity__missing_query_tag(
    db_session: Session,
) -> None:
    """Runs sampling with a missing similarity query tag."""
    collection_id = fill_db_with_samples_and_embeddings(
        db_session, n_samples=5, embedding_model_names=["embedding_model_1"]
    )

    sampling_config = SamplingConfig(
        collection_id=collection_id,
        n_samples_to_select=2,
        sampling_result_tag_name="sampling_1",
        strategies=[
            EmbeddingSimilarityStrategy(
                query_tag_name="missing_query_tag",
                embedding_model_name="embedding_model_1",
            )
        ],
    )

    with pytest.raises(
        ValueError,
        match=r"Query tag with name missing_query_tag not found\.",
    ):
        sampling_via_database(
            db_session,
            sampling_config,
            input_sample_ids=_all_sample_ids(db_session, collection_id),
        )


def test_sampling_via_database__embedding_similarity__query_tag_without_embeddings(
    db_session: Session,
) -> None:
    """Runs sampling with a query tag that has no embeddings."""
    collection_id = fill_db_with_samples_and_embeddings(
        db_session, n_samples=5, embedding_model_names=["embedding_model_1"]
    )
    create_tag(session=db_session, collection_id=collection_id, tag_name="empty_query_tag")

    sampling_config = SamplingConfig(
        collection_id=collection_id,
        n_samples_to_select=2,
        sampling_result_tag_name="sampling_1",
        strategies=[
            EmbeddingSimilarityStrategy(
                query_tag_name="empty_query_tag",
                embedding_model_name="embedding_model_1",
            )
        ],
    )

    with pytest.raises(
        ValueError,
        match=(
            r"Query tag empty_query_tag does not have embeddings for embedding model "
            r"embedding_model_1\."
        ),
    ):
        sampling_via_database(
            db_session,
            sampling_config,
            input_sample_ids=_all_sample_ids(db_session, collection_id),
        )


def test_sampling_via_database__more_samples_to_sampling_than_available(
    db_session: Session,
    mocker: MockerFixture,
) -> None:
    """Runs sampling when requesting more samples than available."""
    collection_id = fill_db_with_samples_and_embeddings(
        db_session, n_samples=5, embedding_model_names=["embedding_model_1"]
    )

    sampling_config = SamplingConfig(
        collection_id=collection_id,
        n_samples_to_select=10,  # Request more samples than available
        sampling_result_tag_name="sampling_1",
        strategies=[EmbeddingDiversityStrategy(embedding_model_name="embedding_model_1")],
    )

    # Spy on the mundig.run method to verify it's called with the correct parameters
    spy_mundig_run = mocker.spy(Mundig, "run")

    sampling_via_database(
        db_session,
        sampling_config,
        input_sample_ids=_all_sample_ids(db_session, collection_id),
    )

    # Verify that mundig.run was called with the correct n_samples (5, not 10)
    spy_mundig_run.assert_called_once_with(self=mocker.ANY, n_samples=5)


def test_sampling_via_database__zero_input_samples_available(
    db_session: Session,
) -> None:
    """Runs sampling when no input samples are available."""
    collection_id = fill_db_with_samples_and_embeddings(
        db_session, n_samples=20, embedding_model_names=["embedding_model_1"]
    )

    # Create a tag with no samples
    _ = tag_resolver.create(
        session=db_session,
        tag=TagCreate(
            collection_id=collection_id,
            name="empty_tag",
            kind="sample",
            description="A tag with no samples",
        ),
    )

    sampling_config = SamplingConfig(
        collection_id=collection_id,
        n_samples_to_select=5,
        sampling_result_tag_name="sampling_1",
        strategies=[EmbeddingDiversityStrategy(embedding_model_name="embedding_model_1")],
    )

    sampling_via_database(db_session, sampling_config, input_sample_ids=[])

    # Assert that no sampling tag was created since there were no samples to sampling
    tags = tag_resolver.get_all_by_collection_id(db_session, collection_id=collection_id)
    tag_names = [tag.name for tag in tags]
    assert "sampling_1" not in tag_names  # Sampling tag should not be created
    assert "empty_tag" in tag_names  # Only the empty tag should exist


def test_sampling_via_database__tag_name_already_exists(
    db_session: Session,
) -> None:
    """Runs sampling when the sampling result tag name already exists."""
    collection_id = fill_db_with_samples_and_embeddings(
        db_session, n_samples=20, embedding_model_names=["embedding_model_1"]
    )

    sampling_config = SamplingConfig(
        collection_id=collection_id,
        n_samples_to_select=5,
        sampling_result_tag_name="sampling_1",  # Same name as existing tag
        strategies=[EmbeddingDiversityStrategy(embedding_model_name="embedding_model_1")],
    )

    candidate_sample_ids = _all_sample_ids(db_session, collection_id)

    # First creation of tag
    sampling_via_database(db_session, sampling_config, input_sample_ids=candidate_sample_ids)

    expected_error = (
        f"Tag with name {sampling_config.sampling_result_tag_name} already exists in the "
        f"collection {collection_id}. Please use a different tag name."
    )
    with pytest.raises(
        ValueError,
        match=expected_error,
    ):
        sampling_via_database(
            db_session,
            sampling_config,
            input_sample_ids=candidate_sample_ids,
        )


def test_sampling_via_database_with_annotation_class_balancing_target(
    db_session: Session,
) -> None:
    """Runs sampling with a simple annotation class balancing strategy."""
    collection_id = fill_db_with_samples_and_embeddings(
        db_session, n_samples=3, embedding_model_names=[]
    )
    sample_ids = _all_sample_ids(db_session, collection_id)

    label_cat = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="cat"
    )
    label_dog = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="dog"
    )
    label_bird = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="bird"
    )

    # Create annotations
    # * sample 0: cat + dog
    # * sample 1: dog
    # * sample 2: dog + bird
    create_annotations(
        session=db_session,
        collection_id=collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=sample_ids[0],
                annotation_label_id=label_cat.annotation_label_id,
            ),
            AnnotationDetails(
                sample_id=sample_ids[0],
                annotation_label_id=label_dog.annotation_label_id,
            ),
            AnnotationDetails(
                sample_id=sample_ids[1],
                annotation_label_id=label_dog.annotation_label_id,
            ),
            AnnotationDetails(
                sample_id=sample_ids[2],
                annotation_label_id=label_dog.annotation_label_id,
            ),
            AnnotationDetails(
                sample_id=sample_ids[2],
                annotation_label_id=label_bird.annotation_label_id,
            ),
        ],
    )

    config = SamplingConfig(
        n_samples_to_select=2,
        collection_id=collection_id,
        sampling_result_tag_name="sampling-tag",
        strategies=[
            AnnotationClassBalancingStrategy(
                target_distribution={
                    "cat": 1,
                    "dog": 1,
                    "bird": 0,
                },
            )
        ],
    )

    sampling_via_database(
        session=db_session,
        config=config,
        input_sample_ids=sample_ids,
    )

    tags = tag_resolver.get_all_by_collection_id(db_session, collection_id=collection_id)
    assert len(tags) == 1
    assert tags[0].name == "sampling-tag"
    samples_in_tag = image_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection_id,
        filters=ImageFilter(sample_filter=SampleFilter(tag_ids=[tags[0].tag_id])),
    ).samples

    sampled_sample_ids = [sample.sample_id for sample in samples_in_tag]
    # Pick the first two samples, because they resemble the [1, 1, 0] label distribution the best.
    assert sampled_sample_ids == [sample_ids[0], sample_ids[1]]


def test_sampling_via_database_with_annotation_class_balancing_missing_class(
    db_session: Session,
) -> None:
    """Runs sampling with a simple annotation class balancing strategy."""
    collection_id = fill_db_with_samples_and_embeddings(
        db_session, n_samples=1, embedding_model_names=[]
    )
    sample_ids = _all_sample_ids(db_session, collection_id)

    config = SamplingConfig(
        n_samples_to_select=2,
        collection_id=collection_id,
        sampling_result_tag_name="sampling-tag",
        strategies=[
            AnnotationClassBalancingStrategy(
                target_distribution={"cat": 1},  # There is no cat label
            )
        ],
    )

    with pytest.raises(ValueError, match="Annotation class with this name does not exist: cat"):
        sampling_via_database(
            session=db_session,
            config=config,
            input_sample_ids=sample_ids,
        )


def test_sampling_via_database_with_annotation_class_balancing_target_incomplete(
    db_session: Session, mocker: MockerFixture
) -> None:
    """Runs sampling with a simple annotation class balancing strategy."""
    collection_id = fill_db_with_samples_and_embeddings(
        db_session, n_samples=3, embedding_model_names=[]
    )
    sample_ids = _all_sample_ids(db_session, collection_id)
    label_cat = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="cat"
    )
    label_dog = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="dog"
    )
    label_bird = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="bird"
    )

    # Create annotations
    # * sample 0: cat + dog
    # * sample 1: cat + bird
    # * sample 2: dog + bird
    create_annotations(
        session=db_session,
        collection_id=collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=sample_ids[0],
                annotation_label_id=label_cat.annotation_label_id,
            ),
            AnnotationDetails(
                sample_id=sample_ids[0],
                annotation_label_id=label_dog.annotation_label_id,
            ),
            AnnotationDetails(
                sample_id=sample_ids[1],
                annotation_label_id=label_cat.annotation_label_id,
            ),
            AnnotationDetails(
                sample_id=sample_ids[1],
                annotation_label_id=label_bird.annotation_label_id,
            ),
            AnnotationDetails(
                sample_id=sample_ids[2],
                annotation_label_id=label_dog.annotation_label_id,
            ),
            AnnotationDetails(
                sample_id=sample_ids[2],
                annotation_label_id=label_bird.annotation_label_id,
            ),
        ],
    )

    config = SamplingConfig(
        n_samples_to_select=2,
        collection_id=collection_id,
        sampling_result_tag_name="sampling-tag",
        strategies=[
            AnnotationClassBalancingStrategy(
                # This distribution gets translated to `cat: 0.5, dog+bird: 0.5`
                target_distribution={
                    "cat": 0.5,
                },
            )
        ],
    )

    spy_mundig_run = mocker.spy(Mundig, "add_class_balancing")
    sampling_via_database(
        session=db_session,
        config=config,
        input_sample_ids=sample_ids,
    )
    tags = tag_resolver.get_all_by_collection_id(session=db_session, collection_id=collection_id)
    assert len(tags) == 1
    assert tags[0].name == "sampling-tag"
    samples_in_tag = image_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection_id,
        filters=ImageFilter(sample_filter=SampleFilter(tag_ids=[tags[0].tag_id])),
    ).samples

    assert len(samples_in_tag) == 2
    # Pick the first two samples, because then the result has exactly 50% of cat.
    assert samples_in_tag[0].sample_id == sample_ids[0]
    assert samples_in_tag[1].sample_id == sample_ids[1]

    spy_mundig_run.assert_called_once()
    call_args = spy_mundig_run.call_args
    np.testing.assert_array_equal(
        call_args.kwargs["class_distributions"],
        np.array([[1.0, 1.0], [1.0, 1.0], [0.0, 2.0]], dtype=np.float32),
    )
    assert call_args.kwargs["target"] == [0.5, 0.5]


def test_sampling_via_database_with_annotation_class_balancing_target_over_1(
    db_session: Session, mocker: MockerFixture
) -> None:
    """Runs sampling with a simple annotation class balancing strategy."""
    collection_id = fill_db_with_samples_and_embeddings(
        db_session, n_samples=3, embedding_model_names=[]
    )
    sample_ids = _all_sample_ids(db_session, collection_id)
    label_cat = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="cat"
    )
    label_dog = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="dog"
    )

    # Create annotations
    # * sample 0: cat
    # * sample 1: dog
    create_annotations(
        session=db_session,
        collection_id=collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=sample_ids[0],
                annotation_label_id=label_cat.annotation_label_id,
            ),
            AnnotationDetails(
                sample_id=sample_ids[1],
                annotation_label_id=label_dog.annotation_label_id,
            ),
        ],
    )

    config = SamplingConfig(
        n_samples_to_select=1,
        collection_id=collection_id,
        sampling_result_tag_name="sampling-tag",
        strategies=[
            AnnotationClassBalancingStrategy(
                # This distribution gets translated to `cat: 1.5, other: 0.0`.
                target_distribution={
                    "cat": 1.5,
                },
            )
        ],
    )

    spy_mundig_run = mocker.spy(Mundig, "add_class_balancing")
    sampling_via_database(
        session=db_session,
        config=config,
        input_sample_ids=sample_ids,
    )
    spy_mundig_run.assert_called_once_with(
        self=mocker.ANY,
        class_distributions=mocker.ANY,
        target=[1.5, 0.0],  # Mundig internally normalizes it to [1, 0].
        strength=1.0,
    )


def test_sampling_via_database_with_annotation_class_balancing_uniform(
    db_session: Session,
) -> None:
    collection_id = fill_db_with_samples_and_embeddings(
        db_session, n_samples=3, embedding_model_names=[]
    )
    sample_ids = _all_sample_ids(db_session, collection_id)

    label_cat = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="cat"
    )
    label_dog = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="dog"
    )
    label_bird = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="bird"
    )

    # Create annotations
    # * sample 0: cat + dog
    # * sample 1: dog
    # * sample 2: dog + bird
    create_annotations(
        session=db_session,
        collection_id=collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=sample_ids[0],
                annotation_label_id=label_cat.annotation_label_id,
            ),
            AnnotationDetails(
                sample_id=sample_ids[0],
                annotation_label_id=label_dog.annotation_label_id,
            ),
            AnnotationDetails(
                sample_id=sample_ids[1],
                annotation_label_id=label_dog.annotation_label_id,
            ),
            AnnotationDetails(
                sample_id=sample_ids[2],
                annotation_label_id=label_dog.annotation_label_id,
            ),
            AnnotationDetails(
                sample_id=sample_ids[2],
                annotation_label_id=label_bird.annotation_label_id,
            ),
        ],
    )

    config = SamplingConfig(
        n_samples_to_select=2,
        collection_id=collection_id,
        sampling_result_tag_name="sampling-tag",
        strategies=[AnnotationClassBalancingStrategy(target_distribution="uniform")],
    )

    sampling_via_database(
        session=db_session,
        config=config,
        input_sample_ids=sample_ids,
    )

    tags = tag_resolver.get_all_by_collection_id(db_session, collection_id=collection_id)
    assert len(tags) == 1
    assert tags[0].name == "sampling-tag"
    samples_in_tag = image_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection_id,
        filters=ImageFilter(sample_filter=SampleFilter(tag_ids=[tags[0].tag_id])),
    ).samples

    sampled_sample_ids = [sample.sample_id for sample in samples_in_tag]
    # Pick the first and last samples, because they resemble the uniform distribution the best.
    assert sampled_sample_ids == [sample_ids[0], sample_ids[2]]


def test_sampling_via_database__annotation_class_balancing__annotation_source(
    db_session: Session,
    mocker: MockerFixture,
) -> None:
    collection_id = fill_db_with_samples_and_embeddings(
        db_session, n_samples=3, embedding_model_names=[]
    )
    sample_ids = _all_sample_ids(db_session, collection_id)

    label_cat = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="cat"
    )
    label_dog = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="dog"
    )
    label_bird = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="bird"
    )

    annotation_source_a_annotations = create_annotations(
        session=db_session,
        collection_id=collection_id,
        collection_name="source-a",
        annotations=[
            AnnotationDetails(
                sample_id=sample_ids[0],
                annotation_label_id=label_cat.annotation_label_id,
            ),
            AnnotationDetails(
                sample_id=sample_ids[1],
                annotation_label_id=label_dog.annotation_label_id,
            ),
            AnnotationDetails(
                sample_id=sample_ids[2],
                annotation_label_id=label_cat.annotation_label_id,
            ),
        ],
    )
    # Source B
    create_annotations(
        session=db_session,
        collection_id=collection_id,
        collection_name="source-b",
        annotations=[
            AnnotationDetails(
                sample_id=sample_ids[2],
                annotation_label_id=label_bird.annotation_label_id,
            ),
        ],
    )

    annotation_source_id = annotation_source_a_annotations[0].sample.collection_id
    add_class_balancing_spy = mocker.spy(Mundig, "add_class_balancing")
    config = SamplingConfig(
        n_samples_to_select=2,
        collection_id=collection_id,
        sampling_result_tag_name="sampling-tag",
        strategies=[
            AnnotationClassBalancingStrategy(
                target_distribution="uniform",
                annotation_source_id=annotation_source_id,
            )
        ],
    )

    sampling_via_database(
        session=db_session,
        config=config,
        input_sample_ids=sample_ids,
    )

    add_class_balancing_spy.assert_called_once()
    class_distributions = add_class_balancing_spy.call_args.kwargs["class_distributions"]
    target = add_class_balancing_spy.call_args.kwargs["target"]

    # Columns are the source-A labels [cat, dog], and source B's bird label is excluded.
    assert class_distributions.shape == (3, 2)
    assert {tuple(class_distributions[:, idx]) for idx in range(class_distributions.shape[1])} == {
        (1.0, 0.0, 1.0),
        (0.0, 1.0, 0.0),
    }
    assert target == pytest.approx([0.5, 0.5], abs=1e-9)


def test_sampling_via_database__annotation_class_balancing__annotation_source_without_labels(
    db_session: Session,
) -> None:
    """Raises a controlled error when the annotation source has no labels for the inputs."""
    collection_id = fill_db_with_samples_and_embeddings(
        db_session, n_samples=3, embedding_model_names=[]
    )
    sample_ids = _all_sample_ids(db_session, collection_id)

    label_cat = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="cat"
    )

    annotations = create_annotations(
        session=db_session,
        collection_id=collection_id,
        collection_name="source-a",
        annotations=[
            AnnotationDetails(
                sample_id=sample_ids[0],
                annotation_label_id=label_cat.annotation_label_id,
            ),
            AnnotationDetails(
                sample_id=sample_ids[1],
                annotation_label_id=label_cat.annotation_label_id,
            ),
        ],
    )
    annotation_source_id = annotations[0].sample.collection_id

    config = SamplingConfig(
        n_samples_to_select=1,
        collection_id=collection_id,
        sampling_result_tag_name="sampling-tag",
        strategies=[
            AnnotationClassBalancingStrategy(
                target_distribution="uniform",
                annotation_source_id=annotation_source_id,
            )
        ],
    )

    with pytest.raises(
        ValueError,
        match=re.escape(
            "Annotation source with the given ID does not contain annotations "
            "for the sampled samples."
        ),
    ):
        sampling_via_database(
            session=db_session,
            config=config,
            input_sample_ids=[sample_ids[2]],
        )


def test_sampling_via_database_with_annotation_class_balancing_input(
    db_session: Session,
) -> None:
    """Runs sampling with a simple annotation class balancing strategy."""
    collection_id = fill_db_with_samples_and_embeddings(
        db_session, n_samples=3, embedding_model_names=[]
    )
    sample_ids = _all_sample_ids(db_session, collection_id)

    label_cat = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="cat"
    )
    label_dog = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="dog"
    )
    label_bird = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="bird"
    )

    # Create annotations
    # * sample 0: cat + dog
    # * sample 1: dog
    # * sample 2: bird
    create_annotations(
        session=db_session,
        collection_id=collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=sample_ids[0],
                annotation_label_id=label_cat.annotation_label_id,
            ),
            AnnotationDetails(
                sample_id=sample_ids[0],
                annotation_label_id=label_dog.annotation_label_id,
            ),
            AnnotationDetails(
                sample_id=sample_ids[1],
                annotation_label_id=label_dog.annotation_label_id,
            ),
            AnnotationDetails(
                sample_id=sample_ids[2],
                annotation_label_id=label_bird.annotation_label_id,
            ),
        ],
    )

    config = SamplingConfig(
        n_samples_to_select=1,
        collection_id=collection_id,
        sampling_result_tag_name="sampling-tag",
        strategies=[AnnotationClassBalancingStrategy(target_distribution="input")],
    )

    sampling_via_database(
        session=db_session,
        config=config,
        input_sample_ids=sample_ids,
    )

    tags = tag_resolver.get_all_by_collection_id(db_session, collection_id=collection_id)
    assert len(tags) == 1
    assert tags[0].name == "sampling-tag"
    samples_in_tag = image_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection_id,
        filters=ImageFilter(sample_filter=SampleFilter(tag_ids=[tags[0].tag_id])),
    ).samples

    assert len(samples_in_tag) == 1
    # Pick the first sample, because it resembles the input distribution the best.
    assert samples_in_tag[0].sample_id == sample_ids[0]


def test_aggregate_class_distributions() -> None:
    """Tests that annotation counting works correctly."""
    label_id_a = uuid4()
    label_id_b = uuid4()
    label_id_c = uuid4()  # This label will be ignored in targets

    sample_id_1 = uuid4()
    sample_id_2 = uuid4()
    sample_id_3 = uuid4()

    target_annotation_ids = [label_id_a, label_id_b]
    input_sample_ids = [sample_id_1, sample_id_2, sample_id_3]

    sample_id_to_annotation_label_ids = {
        sample_id_1: [label_id_a, label_id_b],
        sample_id_2: [label_id_a, label_id_c],  # C should be ignored
        sample_id_3: [label_id_b, label_id_c],  # C should be ignored
    }

    class_distributions = _aggregate_class_distributions(
        input_sample_ids=input_sample_ids,
        sample_id_to_annotation_label_ids=sample_id_to_annotation_label_ids,
        target_annotation_ids=target_annotation_ids,
    )

    # Columns correspond to [label_id_a, label_id_b]
    # Row 0 (Sample 1): 1 A, 1 B
    # Row 1 (Sample 2): 1 A, 0 B (C is ignored)
    # Row 2 (Sample 3): 0 A, 1 B (C is ignored)
    expected_distributions = np.array(
        [
            [1.0, 1.0],
            [1.0, 0.0],
            [0.0, 1.0],
        ],
        dtype=np.float32,
    )
    np.testing.assert_array_equal(class_distributions, expected_distributions)


def _all_sample_ids(session: Session, collection_id: UUID) -> list[UUID]:
    """Return all sample ids for the collection ordered as returned by resolver."""
    samples = image_resolver.get_all_by_collection_id(
        session=session, collection_id=collection_id, pagination=None
    ).samples
    return [sample.sample_id for sample in samples]
