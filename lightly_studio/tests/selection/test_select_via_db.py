"""Test database selection functions."""

from __future__ import annotations

from uuid import UUID, uuid4

import numpy as np
import pytest
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.models.tag import TagCreate
from lightly_studio.resolvers import (
    image_resolver,
    tag_resolver,
)
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from lightly_studio.selection.mundig import Mundig
from lightly_studio.selection.select_via_db import (
    _aggregate_class_distributions,
    _get_class_balancing_data,
    select_via_database,
)
from lightly_studio.selection.selection_config import (
    AnnotationClassBalancingStrategy,
    EmbeddingDiversityStrategy,
    SelectionConfig,
    SelectionStrategy,
)
from tests.helpers_resolvers import (
    AnnotationDetails,
    create_annotation_label,
    create_annotations,
    create_collection,
    fill_db_with_samples_and_embeddings,
)


def test_select_via_database__embedding_diversity(
    test_db: Session,
) -> None:
    """Runs selection with a simple embedding diversity strategy."""
    dataset_id = fill_db_with_samples_and_embeddings(
        test_db, n_samples=20, embedding_model_names=["embedding_model_1"]
    )

    selection_config = SelectionConfig(
        collection_id=dataset_id,
        n_samples_to_select=2,
        selection_result_tag_name="selection_1",
        strategies=[EmbeddingDiversityStrategy(embedding_model_name="embedding_model_1")],
    )

    select_via_database(
        test_db, selection_config, input_sample_ids=_all_sample_ids(test_db, dataset_id)
    )

    # Assert that the tag for the selected set was created with 2 samples
    tags = tag_resolver.get_all_by_collection_id(test_db, collection_id=dataset_id)
    assert len(tags) == 1
    assert tags[0].name == "selection_1"
    samples_in_tag = image_resolver.get_all_by_collection_id(
        session=test_db,
        collection_id=dataset_id,
        filters=ImageFilter(sample_filter=SampleFilter(tag_ids=[tags[0].tag_id])),
    ).samples
    assert len(samples_in_tag) == 2

    # Assert that the samples in the tag are the expected ones:
    # The first sample and most distant one should be selected.
    expected_sample_paths = {"sample_0.jpg", "sample_19.jpg"}
    actual_sample_paths = {sample.file_path_abs for sample in samples_in_tag}
    assert actual_sample_paths == expected_sample_paths


def test_select_via_database__multi_embedding_diversity(
    test_db: Session,
) -> None:
    """Runs selection with multiple embedding diversity strategies."""
    dataset_id = fill_db_with_samples_and_embeddings(
        test_db,
        n_samples=20,
        embedding_model_names=["embedding_model_1", "embedding_model_2"],
    )

    selection_config = SelectionConfig(
        collection_id=dataset_id,
        n_samples_to_select=2,
        selection_result_tag_name="selection_1",
        strategies=[
            EmbeddingDiversityStrategy(embedding_model_name="embedding_model_1"),
            EmbeddingDiversityStrategy(embedding_model_name="embedding_model_2"),
        ],
    )
    select_via_database(
        test_db, selection_config, input_sample_ids=_all_sample_ids(test_db, dataset_id)
    )

    # Assert that the tag for the selected set was created with 2 samples
    tags = tag_resolver.get_all_by_collection_id(test_db, collection_id=dataset_id)
    assert len(tags) == 1
    assert tags[0].name == "selection_1"
    samples_in_tag = image_resolver.get_all_by_collection_id(
        session=test_db,
        collection_id=dataset_id,
        filters=ImageFilter(sample_filter=SampleFilter(tag_ids=[tags[0].tag_id])),
    ).samples

    # Assert that the samples in the tag are the expected ones:
    # The first sample and most distant one should be selected.
    expected_sample_paths = {"sample_0.jpg", "sample_19.jpg"}
    actual_sample_paths = {sample.file_path_abs for sample in samples_in_tag}
    assert actual_sample_paths == expected_sample_paths


def test_select_via_database__embedding_diversity__sample_filter_tags(
    test_db: Session,
) -> None:
    """Runs selection with a filter for the input tag."""
    dataset_id = fill_db_with_samples_and_embeddings(
        test_db, n_samples=101, embedding_model_names=["embedding_model_1"]
    )

    # Create a tag and add some samples to it
    tag = tag_resolver.create(
        session=test_db,
        tag=TagCreate(
            collection_id=dataset_id,
            name="samples_5_through_14",
            kind="sample",
            description="A test tag",
        ),
    )
    all_samples = image_resolver.get_all_by_collection_id(
        session=test_db, pagination=None, collection_id=dataset_id
    ).samples
    assert len(all_samples) == 101
    samples_5_through_14 = sorted(all_samples, key=lambda s: s.created_at)[5:15]
    tag_resolver.add_sample_ids_to_tag_id(
        session=test_db,
        tag_id=tag.tag_id,
        sample_ids=[s.sample_id for s in samples_5_through_14],
    )

    # Run diversity selection with the tag as input
    selection_config = SelectionConfig(
        collection_id=dataset_id,
        n_samples_to_select=2,
        selection_result_tag_name="selection_1",
        strategies=[EmbeddingDiversityStrategy(embedding_model_name="embedding_model_1")],
    )
    select_via_database(
        test_db,
        selection_config,
        input_sample_ids=[s.sample_id for s in samples_5_through_14],
    )

    # Assert that the tag for the selected set was created with 2 samples
    tags = tag_resolver.get_all_by_collection_id(test_db, collection_id=dataset_id)
    assert len(tags) == 2
    tag_selected = next(
        t for t in tags if t.name == "selection_1"
    )  # Get the tag created by the selection
    samples_in_tag = image_resolver.get_all_by_collection_id(
        session=test_db,
        collection_id=dataset_id,
        filters=ImageFilter(sample_filter=SampleFilter(tag_ids=[tag_selected.tag_id])),
    ).samples
    assert len(samples_in_tag) == 2

    # Assert that the samples in the tag are the expected ones:
    # The first sample and most distant one should be selected.
    expected_sample_paths = {"sample_5.jpg", "sample_14.jpg"}
    actual_sample_paths = {sample.file_path_abs for sample in samples_in_tag}
    assert actual_sample_paths == expected_sample_paths


def test_select_via_database__unknown_strategy(
    test_db: Session,
) -> None:
    """Runs selection with a non-existing strategy.

    Check for the correct error message.
    """
    dataset_id = fill_db_with_samples_and_embeddings(
        test_db, n_samples=20, embedding_model_names=["embedding_model_1"]
    )

    selection_config = SelectionConfig(
        collection_id=dataset_id,
        n_samples_to_select=2,
        selection_result_tag_name="selection_1",
        strategies=[SelectionStrategy()],
    )

    expected_error = "Selection strategy of type <class "
    "'lightly_studio.selection.selection_config.SelectionStrategy'> is unknown."
    with pytest.raises(
        ValueError,
        match=expected_error,
    ):
        select_via_database(
            test_db,
            selection_config,
            input_sample_ids=_all_sample_ids(test_db, dataset_id),
        )


def test_select_via_database__more_samples_to_select_than_available(
    test_db: Session,
    mocker: MockerFixture,
) -> None:
    """Runs selection when requesting more samples than available."""
    dataset_id = fill_db_with_samples_and_embeddings(
        test_db, n_samples=5, embedding_model_names=["embedding_model_1"]
    )

    selection_config = SelectionConfig(
        collection_id=dataset_id,
        n_samples_to_select=10,  # Request more samples than available
        selection_result_tag_name="selection_1",
        strategies=[EmbeddingDiversityStrategy(embedding_model_name="embedding_model_1")],
    )

    # Spy on the mundig.run method to verify it's called with the correct parameters
    spy_mundig_run = mocker.spy(Mundig, "run")

    select_via_database(
        test_db,
        selection_config,
        input_sample_ids=_all_sample_ids(test_db, dataset_id),
    )

    # Verify that mundig.run was called with the correct n_samples (5, not 10)
    spy_mundig_run.assert_called_once_with(self=mocker.ANY, n_samples=5)


def test_select_via_database__zero_input_samples_available(
    test_db: Session,
) -> None:
    """Runs selection when no input samples are available."""
    dataset_id = fill_db_with_samples_and_embeddings(
        test_db, n_samples=20, embedding_model_names=["embedding_model_1"]
    )

    # Create a tag with no samples
    _ = tag_resolver.create(
        session=test_db,
        tag=TagCreate(
            collection_id=dataset_id,
            name="empty_tag",
            kind="sample",
            description="A tag with no samples",
        ),
    )

    selection_config = SelectionConfig(
        collection_id=dataset_id,
        n_samples_to_select=5,
        selection_result_tag_name="selection_1",
        strategies=[EmbeddingDiversityStrategy(embedding_model_name="embedding_model_1")],
    )

    select_via_database(test_db, selection_config, input_sample_ids=[])

    # Assert that no selection tag was created since there were no samples to select
    tags = tag_resolver.get_all_by_collection_id(test_db, collection_id=dataset_id)
    tag_names = [tag.name for tag in tags]
    assert "selection_1" not in tag_names  # Selection tag should not be created
    assert "empty_tag" in tag_names  # Only the empty tag should exist


def test_select_via_database__tag_name_already_exists(
    test_db: Session,
) -> None:
    """Runs selection when the selection result tag name already exists."""
    dataset_id = fill_db_with_samples_and_embeddings(
        test_db, n_samples=20, embedding_model_names=["embedding_model_1"]
    )

    selection_config = SelectionConfig(
        collection_id=dataset_id,
        n_samples_to_select=5,
        selection_result_tag_name="selection_1",  # Same name as existing tag
        strategies=[EmbeddingDiversityStrategy(embedding_model_name="embedding_model_1")],
    )

    candidate_sample_ids = _all_sample_ids(test_db, dataset_id)

    # First creation of tag
    select_via_database(test_db, selection_config, input_sample_ids=candidate_sample_ids)

    expected_error = (
        f"Tag with name {selection_config.selection_result_tag_name} already exists in the "
        f"dataset {dataset_id}. Please use a different tag name."
    )
    with pytest.raises(
        ValueError,
        match=expected_error,
    ):
        select_via_database(
            test_db,
            selection_config,
            input_sample_ids=candidate_sample_ids,
        )


def test_select_via_database_with_annotation_class_balancing_target(
    test_db: Session,
) -> None:
    """Runs selection with a simple annotation class balancing strategy."""
    dataset_id = fill_db_with_samples_and_embeddings(test_db, n_samples=3, embedding_model_names=[])
    sample_ids = _all_sample_ids(test_db, dataset_id)

    label_cat = create_annotation_label(
        session=test_db, root_collection_id=dataset_id, label_name="cat"
    )
    label_dog = create_annotation_label(
        session=test_db, root_collection_id=dataset_id, label_name="dog"
    )
    label_bird = create_annotation_label(
        session=test_db, root_collection_id=dataset_id, label_name="bird"
    )

    # Create annotations
    # * sample 0: cat + dog
    # * sample 1: dog
    # * sample 2: dog + bird
    create_annotations(
        session=test_db,
        collection_id=dataset_id,
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

    config = SelectionConfig(
        n_samples_to_select=2,
        collection_id=dataset_id,
        selection_result_tag_name="selection-tag",
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

    select_via_database(
        session=test_db,
        config=config,
        input_sample_ids=sample_ids,
    )

    tags = tag_resolver.get_all_by_collection_id(test_db, collection_id=dataset_id)
    assert len(tags) == 1
    assert tags[0].name == "selection-tag"
    samples_in_tag = image_resolver.get_all_by_collection_id(
        session=test_db,
        collection_id=dataset_id,
        filters=ImageFilter(sample_filter=SampleFilter(tag_ids=[tags[0].tag_id])),
    ).samples

    selected_sample_ids = [sample.sample_id for sample in samples_in_tag]
    # Pick the first two samples, because they resemble the [1, 1, 0] label distribution the best.
    assert selected_sample_ids == [sample_ids[0], sample_ids[1]]


def test_select_via_database_with_annotation_class_balancing_missing_class(
    test_db: Session,
) -> None:
    """Runs selection with a simple annotation class balancing strategy."""
    dataset_id = fill_db_with_samples_and_embeddings(test_db, n_samples=1, embedding_model_names=[])
    sample_ids = _all_sample_ids(test_db, dataset_id)

    config = SelectionConfig(
        n_samples_to_select=2,
        collection_id=dataset_id,
        selection_result_tag_name="selection-tag",
        strategies=[
            AnnotationClassBalancingStrategy(
                target_distribution={"cat": 1},  # There is no cat label
            )
        ],
    )

    with pytest.raises(ValueError, match="Annotation label with this name does not exist: cat"):
        select_via_database(
            session=test_db,
            config=config,
            input_sample_ids=sample_ids,
        )


def test_select_via_database_with_annotation_class_balancing_target_incomplete(
    test_db: Session, mocker: MockerFixture
) -> None:
    """Runs selection with a simple annotation class balancing strategy."""
    dataset_id = fill_db_with_samples_and_embeddings(test_db, n_samples=3, embedding_model_names=[])
    sample_ids = _all_sample_ids(test_db, dataset_id)
    label_cat = create_annotation_label(
        session=test_db, root_collection_id=dataset_id, label_name="cat"
    )
    label_dog = create_annotation_label(
        session=test_db, root_collection_id=dataset_id, label_name="dog"
    )
    label_bird = create_annotation_label(
        session=test_db, root_collection_id=dataset_id, label_name="bird"
    )

    # Create annotations
    # * sample 0: cat + dog
    # * sample 1: cat + bird
    # * sample 2: dog + bird
    create_annotations(
        session=test_db,
        collection_id=dataset_id,
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

    config = SelectionConfig(
        n_samples_to_select=2,
        collection_id=dataset_id,
        selection_result_tag_name="selection-tag",
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
    select_via_database(
        session=test_db,
        config=config,
        input_sample_ids=sample_ids,
    )
    tags = tag_resolver.get_all_by_collection_id(session=test_db, collection_id=dataset_id)
    assert len(tags) == 1
    assert tags[0].name == "selection-tag"
    samples_in_tag = image_resolver.get_all_by_collection_id(
        session=test_db,
        collection_id=dataset_id,
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


def test_select_via_database_with_annotation_class_balancing_target_over_1(
    test_db: Session, mocker: MockerFixture
) -> None:
    """Runs selection with a simple annotation class balancing strategy."""
    dataset_id = fill_db_with_samples_and_embeddings(test_db, n_samples=3, embedding_model_names=[])
    sample_ids = _all_sample_ids(test_db, dataset_id)
    label_cat = create_annotation_label(
        session=test_db, root_collection_id=dataset_id, label_name="cat"
    )
    label_dog = create_annotation_label(
        session=test_db, root_collection_id=dataset_id, label_name="dog"
    )

    # Create annotations
    # * sample 0: cat
    # * sample 1: dog
    create_annotations(
        session=test_db,
        collection_id=dataset_id,
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

    config = SelectionConfig(
        n_samples_to_select=1,
        collection_id=dataset_id,
        selection_result_tag_name="selection-tag",
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
    select_via_database(
        session=test_db,
        config=config,
        input_sample_ids=sample_ids,
    )
    spy_mundig_run.assert_called_once_with(
        self=mocker.ANY,
        class_distributions=mocker.ANY,
        target=[1.5, 0.0],  # Mundig internally normalizes it to [1, 0].
        strength=1.0,
    )


def test_select_via_database_with_annotation_class_balancing_uniform(
    test_db: Session,
) -> None:
    """Runs selection with a simple annotation class balancing strategy."""
    dataset_id = fill_db_with_samples_and_embeddings(test_db, n_samples=3, embedding_model_names=[])
    sample_ids = _all_sample_ids(test_db, dataset_id)

    label_cat = create_annotation_label(
        session=test_db, root_collection_id=dataset_id, label_name="cat"
    )
    label_dog = create_annotation_label(
        session=test_db, root_collection_id=dataset_id, label_name="dog"
    )
    label_bird = create_annotation_label(
        session=test_db, root_collection_id=dataset_id, label_name="bird"
    )

    # Create annotations
    # * sample 0: cat + dog
    # * sample 1: dog
    # * sample 2: dog + bird
    create_annotations(
        session=test_db,
        collection_id=dataset_id,
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

    config = SelectionConfig(
        n_samples_to_select=2,
        collection_id=dataset_id,
        selection_result_tag_name="selection-tag",
        strategies=[AnnotationClassBalancingStrategy(target_distribution="uniform")],
    )

    select_via_database(
        session=test_db,
        config=config,
        input_sample_ids=sample_ids,
    )

    tags = tag_resolver.get_all_by_collection_id(test_db, collection_id=dataset_id)
    assert len(tags) == 1
    assert tags[0].name == "selection-tag"
    samples_in_tag = image_resolver.get_all_by_collection_id(
        session=test_db,
        collection_id=dataset_id,
        filters=ImageFilter(sample_filter=SampleFilter(tag_ids=[tags[0].tag_id])),
    ).samples

    selected_sample_ids = [sample.sample_id for sample in samples_in_tag]
    # Pick the first and last samples, because they resemble the uniform distribution the best.
    assert selected_sample_ids == [sample_ids[0], sample_ids[2]]


def test_select_via_database_with_annotation_class_balancing_input(
    test_db: Session,
) -> None:
    """Runs selection with a simple annotation class balancing strategy."""
    dataset_id = fill_db_with_samples_and_embeddings(test_db, n_samples=3, embedding_model_names=[])
    sample_ids = _all_sample_ids(test_db, dataset_id)

    label_cat = create_annotation_label(
        session=test_db, root_collection_id=dataset_id, label_name="cat"
    )
    label_dog = create_annotation_label(
        session=test_db, root_collection_id=dataset_id, label_name="dog"
    )
    label_bird = create_annotation_label(
        session=test_db, root_collection_id=dataset_id, label_name="bird"
    )

    # Create annotations
    # * sample 0: cat + dog
    # * sample 1: dog
    # * sample 2: bird
    create_annotations(
        session=test_db,
        collection_id=dataset_id,
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

    config = SelectionConfig(
        n_samples_to_select=1,
        collection_id=dataset_id,
        selection_result_tag_name="selection-tag",
        strategies=[AnnotationClassBalancingStrategy(target_distribution="input")],
    )

    select_via_database(
        session=test_db,
        config=config,
        input_sample_ids=sample_ids,
    )

    tags = tag_resolver.get_all_by_collection_id(test_db, collection_id=dataset_id)
    assert len(tags) == 1
    assert tags[0].name == "selection-tag"
    samples_in_tag = image_resolver.get_all_by_collection_id(
        session=test_db,
        collection_id=dataset_id,
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


def test_get_class_balancing_data_input(test_db: Session) -> None:
    """Test the 'input' distribution logic."""
    root_dataset_id = UUID("00000000-0000-0000-0000-000000000000")
    label_id_cat = UUID("00000000-0000-0000-0000-000000000001")
    label_id_dog = UUID("00000000-0000-0000-0000-000000000002")
    sample_id_1 = UUID("11111111-1111-1111-1111-111111111111")
    sample_id_2 = UUID("22222222-2222-2222-2222-222222222222")

    # The order of target keys depends on the insertion order in this list.
    # 'cat' appears first, 'dog' appears second.
    # Target Keys: [cat, dog]
    all_annotation_labels = [label_id_cat, label_id_cat, label_id_dog]
    input_sample_ids = [sample_id_1, sample_id_2]

    sample_id_to_annotation_label_ids = {
        sample_id_1: [label_id_cat],
        sample_id_2: [label_id_cat, label_id_dog],
    }

    strat = AnnotationClassBalancingStrategy(target_distribution="input")

    class_dist, target_vals = _get_class_balancing_data(
        session=test_db,
        strat=strat,
        root_dataset_id=root_dataset_id,
        annotation_label_ids=all_annotation_labels,
        input_sample_ids=input_sample_ids,
        sample_id_to_annotation_label_ids=sample_id_to_annotation_label_ids,
    )

    expected_vals = [2, 1]
    assert target_vals == expected_vals

    # Columns: [Cat, Dog]
    # Row 0 (Sample 1): 1 Cat, 0 Dog
    # Row 1 (Sample 2): 1 Cat, 1 Dog
    expected_dist = np.array([[1.0, 0.0], [1.0, 1.0]])
    np.testing.assert_array_equal(class_dist, expected_dist)


def test_get_class_balancing_data_uniform(test_db: Session) -> None:
    """Test the 'uniform' distribution logic."""
    root_dataset_id = UUID("00000000-0000-0000-0000-000000000000")
    label_id_cat = UUID("00000000-0000-0000-0000-000000000001")
    label_id_dog = UUID("00000000-0000-0000-0000-000000000002")
    sample_id_1 = UUID("11111111-1111-1111-1111-111111111111")
    sample_id_2 = UUID("22222222-2222-2222-2222-222222222222")

    all_annotation_labels = [label_id_cat, label_id_cat, label_id_dog]
    input_sample_ids = [sample_id_1, sample_id_2]

    sample_id_to_annotation_label_ids = {
        sample_id_1: [label_id_cat],
        sample_id_2: [label_id_cat, label_id_dog],
    }

    strat = AnnotationClassBalancingStrategy(target_distribution="uniform")

    class_dist, target_vals = _get_class_balancing_data(
        session=test_db,
        strat=strat,
        root_dataset_id=root_dataset_id,
        annotation_label_ids=all_annotation_labels,
        input_sample_ids=input_sample_ids,
        sample_id_to_annotation_label_ids=sample_id_to_annotation_label_ids,
    )

    assert len(target_vals) == 2
    assert target_vals == pytest.approx([0.5, 0.5], abs=1e-9)

    expected_col_cat = np.array([1.0, 1.0], dtype=np.float32)
    expected_col_dog = np.array([0.0, 1.0], dtype=np.float32)

    np.testing.assert_array_equal(class_dist[:, 0], expected_col_cat)
    np.testing.assert_array_equal(class_dist[:, 1], expected_col_dog)


def test_get_class_balancing_data_target(test_db: Session) -> None:
    """Test the 'target' (dict) distribution logic."""
    collection_id = create_collection(session=test_db).collection_id
    label_cat_obj = create_annotation_label(
        session=test_db, root_collection_id=collection_id, label_name="cat"
    )
    label_dog_obj = create_annotation_label(
        session=test_db, root_collection_id=collection_id, label_name="dog"
    )

    label_id_cat = label_cat_obj.annotation_label_id
    label_id_dog = label_dog_obj.annotation_label_id

    sample_id_1 = UUID("11111111-1111-1111-1111-111111111111")
    sample_id_2 = UUID("22222222-2222-2222-2222-222222222222")

    all_annotation_labels = [label_id_cat, label_id_cat, label_id_dog]
    input_sample_ids = [sample_id_1, sample_id_2]

    sample_id_to_annotation_label_ids = {
        sample_id_1: [label_id_cat],
        sample_id_2: [label_id_cat, label_id_dog],
    }

    distribution_dict = {
        "dog": 0.7,
        "cat": 0.3,
    }

    strat = AnnotationClassBalancingStrategy(target_distribution=distribution_dict)

    class_dist, target_vals = _get_class_balancing_data(
        session=test_db,
        strat=strat,
        root_dataset_id=dataset_id,
        annotation_label_ids=all_annotation_labels,
        input_sample_ids=input_sample_ids,
        sample_id_to_annotation_label_ids=sample_id_to_annotation_label_ids,
    )

    expected_vals = [0.7, 0.3]
    assert target_vals == pytest.approx(expected_vals, abs=1e-9)

    expected_dist = np.array([[0.0, 1.0], [1.0, 1.0]])
    np.testing.assert_array_equal(class_dist, expected_dist)


def _all_sample_ids(session: Session, dataset_id: UUID) -> list[UUID]:
    """Return all sample ids for the dataset ordered as returned by resolver."""
    samples = image_resolver.get_all_by_collection_id(
        session=session, collection_id=dataset_id, pagination=None
    ).samples
    return [sample.sample_id for sample in samples]
