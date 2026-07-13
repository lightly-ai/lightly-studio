"""Database sampling functions for the sampling process."""

from __future__ import annotations

import logging
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from uuid import UUID, uuid4

import numpy as np
import sqlalchemy
from numpy.typing import NDArray
from sqlmodel import Session, col, select

from lightly_studio.database.db_vector import Embedding
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.tag import TagCreate
from lightly_studio.resolvers import (
    annotation_label_resolver,
    annotation_resolver,
    collection_resolver,
    embedding_model_resolver,
    metadata_resolver,
    sample_embedding_resolver,
    tag_resolver,
)
from lightly_studio.resolvers.metadata_resolver.sample.get_metadata_info import (
    CATEGORICAL_METADATA_TYPES,
    format_categorical_value,
)
from lightly_studio.resolvers.metadata_resolver.sample.get_metadata_values_for_key import (
    get_metadata_values_for_key,
)
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from lightly_studio.sampling.mundig import Mundig
from lightly_studio.sampling.sampling_config import (
    AnnotationClassBalancingStrategy,
    EmbeddingDeduplicationStrategy,
    EmbeddingDiversityStrategy,
    EmbeddingSimilarityStrategy,
    MetadataClassBalancingStrategy,
    MetadataWeightingStrategy,
    SamplingConfig,
)
from lightly_studio.utils import batching

EPSILON = 1e-6

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _SamplingContext:
    """Shared inputs used while resolving sampling strategies."""

    collection_id: UUID
    dataset_id: UUID
    input_sample_ids: list[UUID]


def _aggregate_class_distributions(
    input_sample_ids: Sequence[UUID],
    sample_id_to_annotation_label_ids: Mapping[UUID, list[UUID]],
    target_annotation_ids: list[UUID],
) -> NDArray[np.float32]:
    """Aggregates class distributions for a list of samples.

    Args:
        input_sample_ids:
            A list of sample IDs for which to aggregate the class distributions.
        sample_id_to_annotation_label_ids:
            A dictionary mapping sample IDs to a list of their annotation class IDs.
        target_annotation_ids:
            A list of annotation class IDs that are considered for the distribution.
            The order of these IDs determines the order of the columns in the output.

    Returns:
        A numpy array of shape (n_samples, n_labels) where n_samples is the
        number of input samples and n_labels is the number of target annotation
        classes. Each row in the array represents the class distribution for a
        sample, where the values are the counts of each target annotation class.
    """
    n_samples = len(input_sample_ids)
    n_labels = len(target_annotation_ids)

    class_distributions = np.zeros((n_samples, n_labels), dtype=np.float32)
    annotation_id_to_idx = {
        annotation_id: j for j, annotation_id in enumerate(target_annotation_ids)
    }
    for i, sample_id in enumerate(input_sample_ids):
        for annotation_label_id in sample_id_to_annotation_label_ids[sample_id]:
            label_idx = annotation_id_to_idx.get(annotation_label_id)
            if label_idx is not None:
                class_distributions[i, label_idx] += 1

    return class_distributions


def _process_explicit_target_distribution(
    session: Session,
    dataset_id: UUID,
    target_distribution: dict[str, float],
    annotation_label_ids: Sequence[UUID],
) -> tuple[dict[UUID, float], set[UUID], float]:
    """Processes the explicit target distribution.

    Args:
        session: The SQLAlchemy session.
        dataset_id: The dataset ID to look for annotation classes.
        target_distribution:
            A dictionary mapping annotation class names to their target proportions.
        annotation_label_ids:
            A sequence of all annotation class IDs to consider for class balancing.

    Returns:
        Tuple of:
            A dictionary mapping annotation class IDs to their effective target proportions.
            The set of unused annotation class IDs
            The target value remaining to 1.0.

    Raises:
        NotImplementedError: If multiple annotation classes with the same name are found.
        ValueError: If an annotation class name does not exist or if targets sum
            to less than 1.0 and all classes are used.
    """
    label_id_to_target: dict[UUID, float] = {}
    total_targets = 0.0
    for label_name, target in target_distribution.items():
        try:
            annotation_label = annotation_label_resolver.get_by_label_name(
                session=session,
                dataset_id=dataset_id,
                label_name=label_name,
            )
        except sqlalchemy.exc.MultipleResultsFound as e:
            raise NotImplementedError(
                "Multiple annotation classes with the same name not supported yet."
            ) from e
        if annotation_label is None:
            raise ValueError(f"Annotation class with this name does not exist: {label_name}")
        label_id_to_target[annotation_label.annotation_label_id] = target
        total_targets += target

    all_label_ids = set(annotation_label_ids)
    unused_label_ids = all_label_ids - set(label_id_to_target.keys())
    # `total_targets` can be more or less than 1.0. Both can be ignored, sampling will still
    # try correctly to reach the target.
    remaining_ratio = max(1.0 - total_targets, 0.0)
    return label_id_to_target, unused_label_ids, remaining_ratio


def _get_class_balancing_data(  # noqa: C901
    session: Session,
    strat: AnnotationClassBalancingStrategy,
    dataset_id: UUID,
    input_sample_ids: Sequence[UUID],
    annotation_label_ids: Sequence[UUID] | None = None,
) -> tuple[NDArray[np.float32], list[float]]:
    """Helper function to get class balancing data."""
    annotations = _get_annotations_for_class_balancing(
        session=session,
        parent_sample_ids=input_sample_ids,
        annotation_source_id=strat.annotation_source_id,
    )
    if strat.annotation_source_id is not None and not annotations:
        raise ValueError(
            "Annotation source with the given ID does not contain annotations "
            "for the sampled samples."
        )

    if annotation_label_ids is None:
        annotation_label_ids = [annotation.annotation_label_id for annotation in annotations]
    sample_id_to_annotation_label_ids = defaultdict(list)
    for annotation in annotations:
        sample_id_to_annotation_label_ids[annotation.parent_sample_id].append(
            annotation.annotation_label_id
        )

    if strat.target_distribution == "uniform":
        # Keep first-seen order so the distribution columns stay stable and line up with values.
        target_keys = list(dict.fromkeys(annotation_label_ids))
        if not target_keys:
            return np.zeros((len(input_sample_ids), 0), dtype=np.float32), []
        target_values = [1.0 / len(target_keys)] * len(target_keys)
    elif strat.target_distribution == "input":
        # Count the number of times each label appears in the input
        input_label_count = Counter(annotation_label_ids)
        target_keys, target_values = (
            list(input_label_count.keys()),
            list(input_label_count.values()),
        )
    elif isinstance(strat.target_distribution, dict):
        label_id_to_target, unused_label_ids, remaining_ratio = (
            _process_explicit_target_distribution(
                session=session,
                dataset_id=dataset_id,
                target_distribution=strat.target_distribution,
                annotation_label_ids=annotation_label_ids,
            )
        )
        if len(unused_label_ids) >= 1:
            other_uuid = uuid4()
            # Handle the case when not all classes have a target.
            # We replace UUIDs that are present in `unused_label_ids` for `other_uuid` and the
            # target for `other_uuid` is `remaining_ratio`.
            for sample_annotation_label_ids in sample_id_to_annotation_label_ids.values():
                for i, label_id in enumerate(sample_annotation_label_ids):
                    if label_id in unused_label_ids:
                        sample_annotation_label_ids[i] = other_uuid
            label_id_to_target[other_uuid] = remaining_ratio

        target_keys, target_values = (
            list(label_id_to_target.keys()),
            list(label_id_to_target.values()),
        )
    else:
        raise ValueError(f"Unknown distribution type: {type(strat.target_distribution)}")

    class_distributions = _aggregate_class_distributions(
        input_sample_ids=input_sample_ids,
        sample_id_to_annotation_label_ids=sample_id_to_annotation_label_ids,
        target_annotation_ids=target_keys,
    )
    return class_distributions, target_values


# Sentinel column for present metadata values not named in an explicit target.
_OTHER_METADATA_VALUE = object()


def _get_metadata_balancing_data(
    session: Session,
    strat: MetadataClassBalancingStrategy,
    collection_id: UUID,
    input_sample_ids: Sequence[UUID],
) -> tuple[NDArray[np.float32], list[float]]:
    """Build the one-hot distribution matrix and target vector for metadata balancing.

    Each in-scope sample contributes a single categorical value, so its row is a
    one-hot vector (contrast: annotation balancing builds multi-label count rows).
    Samples missing the key contribute an all-zero row and therefore do not
    influence this strategy.

    Raises:
        ValueError: If the key is absent from the collection or is not categorical.
    """
    sample_to_value, metadata_type = get_metadata_values_for_key(
        session=session, collection_id=collection_id, key=strat.metadata_key
    )
    if metadata_type is None:
        raise ValueError(
            f"Metadata key '{strat.metadata_key}' not found in collection {collection_id}."
        )
    if metadata_type not in CATEGORICAL_METADATA_TYPES:
        raise ValueError(
            f"Metadata key '{strat.metadata_key}' has type {metadata_type!r}; balancing "
            f"requires a categorical key (one of {CATEGORICAL_METADATA_TYPES})."
        )

    # Per input sample: its single display value, or absent when the key is missing.
    sample_value_by_id: dict[UUID, str] = {
        sample_id: format_categorical_value(sample_to_value[sample_id])
        for sample_id in input_sample_ids
        if sample_id in sample_to_value
    }
    present_values = [
        sample_value_by_id[sample_id]
        for sample_id in input_sample_ids
        if sample_id in sample_value_by_id
    ]

    column_value_by_id: Mapping[UUID, object] = sample_value_by_id
    if strat.target_distribution == "uniform":
        # Keep first-seen order so the distribution columns stay stable.
        target_keys: list[object] = list(dict.fromkeys(present_values))
        if not target_keys:
            return np.zeros((len(input_sample_ids), 0), dtype=np.float32), []
        target_values = [1.0 / len(target_keys)] * len(target_keys)
    elif strat.target_distribution == "input":
        value_count = Counter(present_values)
        target_keys = list(value_count.keys())
        target_values = [float(count) for count in value_count.values()]
    elif isinstance(strat.target_distribution, dict):
        target_keys, target_values, column_value_by_id = _explicit_metadata_target(
            target_distribution=strat.target_distribution,
            sample_value_by_id=sample_value_by_id,
            present_values=present_values,
        )
    else:
        raise ValueError(f"Unknown distribution type: {type(strat.target_distribution)}")

    matrix = _build_one_hot_matrix(
        input_sample_ids=input_sample_ids,
        column_value_by_id=column_value_by_id,
        target_keys=target_keys,
    )
    return matrix, target_values


def _explicit_metadata_target(
    target_distribution: dict[str, float],
    sample_value_by_id: Mapping[UUID, str],
    present_values: Sequence[str],
) -> tuple[list[object], list[float], dict[UUID, object]]:
    """Resolve an explicit metadata target distribution.

    Named values keep their target. Present values that are not named collapse
    into a single "other" bucket whose target is the ratio remaining to 1.0.
    """
    value_to_target: dict[object, float] = {}
    value_to_target.update(target_distribution)
    total_targets = sum(target_distribution.values())
    remaining_ratio = max(1.0 - total_targets, 0.0)

    unlisted_values = set(present_values) - set(target_distribution.keys())
    column_value_by_id: dict[UUID, object] = dict(sample_value_by_id)
    if unlisted_values:
        for sample_id, value in sample_value_by_id.items():
            if value in unlisted_values:
                column_value_by_id[sample_id] = _OTHER_METADATA_VALUE
        value_to_target[_OTHER_METADATA_VALUE] = remaining_ratio

    return list(value_to_target.keys()), list(value_to_target.values()), column_value_by_id


def _build_one_hot_matrix(
    input_sample_ids: Sequence[UUID],
    column_value_by_id: Mapping[UUID, object],
    target_keys: Sequence[object],
) -> NDArray[np.float32]:
    """One-hot each sample's value into the target column for that value.

    Samples absent from ``column_value_by_id`` (missing key) or whose value is
    not a target column stay all-zero and do not influence balancing.
    """
    value_to_idx = {value: idx for idx, value in enumerate(target_keys)}
    matrix = np.zeros((len(input_sample_ids), len(target_keys)), dtype=np.float32)
    for row, sample_id in enumerate(input_sample_ids):
        value = column_value_by_id.get(sample_id)
        idx = value_to_idx.get(value) if value is not None else None
        if idx is not None:
            matrix[row, idx] = 1.0
    return matrix


def sampling_via_database(
    session: Session, config: SamplingConfig, input_sample_ids: list[UUID]
) -> None:
    """Run sampling using the provided candidate sample ids.

    First resolves the sampling config to concrete database values.
    Then calls Mundig to run the sampling with pure values.
    Finally creates a tag for the selected set.
    """
    # Check if the tag name is already used
    existing_tag = tag_resolver.get_by_name(
        session=session,
        tag_name=config.sampling_result_tag_name,
        collection_id=config.collection_id,
    )
    if existing_tag:
        msg = (
            f"Tag with name {config.sampling_result_tag_name} already exists in the "
            f"collection {config.collection_id}. Please use a different tag name."
        )
        raise ValueError(msg)

    n_samples_to_select = min(config.n_samples_to_select, len(input_sample_ids))
    if n_samples_to_select == 0:
        logger.warning("No samples available for sampling.")
        return

    # Get root dataset id for balancing strategies
    root_collection = collection_resolver.get_root_collection(
        session=session, collection_id=config.collection_id
    )
    dataset_id = root_collection.dataset_id
    context = _SamplingContext(
        collection_id=config.collection_id,
        dataset_id=dataset_id,
        input_sample_ids=input_sample_ids,
    )

    mundig = Mundig()
    for strat in config.strategies:
        _add_strategy_to_mundig(
            session=session,
            context=context,
            strat=strat,
            mundig=mundig,
        )

    selected_indices = mundig.run(n_samples=n_samples_to_select)
    selected_sample_ids = [input_sample_ids[i] for i in selected_indices]

    tag = tag_resolver.create(
        session=session,
        tag=TagCreate(
            collection_id=config.collection_id,
            name=config.sampling_result_tag_name,
            kind="sample",
        ),
    )
    tag_resolver.add_sample_ids_to_tag_id(
        session=session, tag_id=tag.tag_id, sample_ids=selected_sample_ids
    )


def _get_embeddings_by_sample_ids(
    session: Session,
    context: _SamplingContext,
    embedding_model_name: str | None,
) -> list[Embedding]:
    """Resolve sample embeddings for the given model and sample ids."""
    embedding_model_id = embedding_model_resolver.get_by_name(
        session=session,
        collection_id=context.collection_id,
        embedding_model_name=embedding_model_name,
    ).embedding_model_id
    embedding_tables = sample_embedding_resolver.get_by_sample_ids(
        session=session,
        sample_ids=list(context.input_sample_ids),
        embedding_model_id=embedding_model_id,
    )
    return [embedding.embedding for embedding in embedding_tables]


def _get_annotations_for_class_balancing(
    session: Session,
    parent_sample_ids: Sequence[UUID],
    annotation_source_id: UUID | None,
) -> list[AnnotationBaseTable]:
    """Resolve annotations that should contribute to class balancing."""
    if annotation_source_id is None:
        return list(
            annotation_resolver.get_all_by_parent_sample_ids(
                session=session,
                parent_sample_ids=parent_sample_ids,
            )
        )

    annotations: list[AnnotationBaseTable] = []
    for batch in batching.batched(items=parent_sample_ids):
        annotations_statement = (
            select(AnnotationBaseTable)
            .join(
                SampleTable,
                col(SampleTable.sample_id) == col(AnnotationBaseTable.sample_id),
            )
            .where(col(AnnotationBaseTable.parent_sample_id).in_(batch))
            .where(col(SampleTable.collection_id) == annotation_source_id)
        )
        annotations.extend(session.exec(annotations_statement).all())
    return annotations


def _add_similarity_to_mundig(
    session: Session,
    context: _SamplingContext,
    strat: EmbeddingSimilarityStrategy,
    mundig: Mundig,
) -> None:
    """Resolve an embedding similarity strategy against a query tag and add it to Mundig."""
    embeddings = _get_embeddings_by_sample_ids(
        session=session,
        context=context,
        embedding_model_name=strat.embedding_model_name,
    )
    embedding_model_id = embedding_model_resolver.get_by_name(
        session=session,
        collection_id=context.collection_id,
        embedding_model_name=strat.embedding_model_name,
    ).embedding_model_id
    query_tag = tag_resolver.get_by_name(
        session=session,
        tag_name=strat.query_tag_name,
        collection_id=context.collection_id,
    )
    if query_tag is None:
        raise ValueError(f"Query tag with name {strat.query_tag_name} not found.")
    query_embedding_tables = sample_embedding_resolver.get_all_by_collection_id(
        session=session,
        collection_id=context.collection_id,
        embedding_model_id=embedding_model_id,
        filters=SampleFilter(tag_ids=[query_tag.tag_id]),
    )
    query_embeddings = [embedding.embedding for embedding in query_embedding_tables]
    if not query_embeddings:
        raise ValueError(
            "Query tag "
            f"{strat.query_tag_name} does not have embeddings for embedding model "
            f"{strat.embedding_model_name}."
        )
    mundig.add_similarity(
        embeddings=embeddings,
        query_embeddings=query_embeddings,
        strength=strat.strength,
    )


def _add_strategy_to_mundig(
    session: Session,
    context: _SamplingContext,
    strat: object,
    mundig: Mundig,
) -> None:
    """Resolve one sampling strategy and add it to Mundig."""
    if isinstance(strat, EmbeddingDiversityStrategy):
        mundig.add_diversity(
            embeddings=_get_embeddings_by_sample_ids(
                session=session,
                context=context,
                embedding_model_name=strat.embedding_model_name,
            ),
            strength=strat.strength,
        )
    elif isinstance(strat, EmbeddingDeduplicationStrategy):
        mundig.add_diversity(
            embeddings=_get_embeddings_by_sample_ids(
                session=session,
                context=context,
                embedding_model_name=strat.embedding_model_name,
            ),
            strength=strat.strength,
            stopping_condition_minimum_distance=strat.stopping_condition_minimum_distance,
        )
    elif isinstance(strat, EmbeddingSimilarityStrategy):
        _add_similarity_to_mundig(session=session, context=context, strat=strat, mundig=mundig)
    elif isinstance(strat, MetadataWeightingStrategy):
        weights: list[float] = []
        metadata_key = strat.metadata_key
        for sample_id in context.input_sample_ids:
            weight = metadata_resolver.get_value_for_sample(session, sample_id, key=metadata_key)
            if not isinstance(weight, (float, int)):
                raise ValueError(
                    f"Metadata {metadata_key} is not a number, only numbers can be used as weights"
                )
            weights.append(float(weight))
        mundig.add_weighting(
            weights=weights,
            strength=strat.strength,
        )
    elif isinstance(strat, AnnotationClassBalancingStrategy):
        class_distributions, target_values = _get_class_balancing_data(
            session=session,
            strat=strat,
            dataset_id=context.dataset_id,
            input_sample_ids=context.input_sample_ids,
        )
        mundig.add_class_balancing(
            class_distributions=class_distributions,
            target=target_values,
            strength=strat.strength,
        )
    elif isinstance(strat, MetadataClassBalancingStrategy):
        _add_metadata_class_balancing_to_mundig(
            session=session, context=context, strat=strat, mundig=mundig
        )
    else:
        raise ValueError(f"Sampling strategy of type {type(strat)} is unknown.")


def _add_metadata_class_balancing_to_mundig(
    session: Session,
    context: _SamplingContext,
    strat: MetadataClassBalancingStrategy,
    mundig: Mundig,
) -> None:
    """Resolve a categorical metadata balancing strategy and add it to Mundig."""
    class_distributions, target_values = _get_metadata_balancing_data(
        session=session,
        strat=strat,
        collection_id=context.collection_id,
        input_sample_ids=context.input_sample_ids,
    )
    mundig.add_class_balancing(
        class_distributions=class_distributions,
        target=target_values,
        strength=strat.strength,
    )
