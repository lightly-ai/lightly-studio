"""Database selection functions for the selection process."""

from __future__ import annotations

import datetime
from collections import Counter, defaultdict
from typing import Mapping, Sequence
from uuid import UUID

import numpy as np
from numpy.typing import NDArray
from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.tag import TagCreate
from lightly_studio.resolvers import (
    annotation_resolver,
    embedding_model_resolver,
    metadata_resolver,
    sample_embedding_resolver,
    tag_resolver,
)
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter
from lightly_studio.selection.mundig import Mundig
from lightly_studio.selection.selection_config import (
    AnnotationClassBalancingStrategy,
    EmbeddingDiversityStrategy,
    MetadataWeightingStrategy,
    SelectionConfig,
)


def _aggregate_class_distributions(
    input_sample_ids: Sequence[UUID],
    sample_id_to_annotations: Mapping[UUID, Sequence[AnnotationBaseTable]],
    target_annotation_ids: list[UUID],
) -> NDArray[np.float32]:
    """Aggregates class distributions for a list of samples.

    Args:
        input_sample_ids:
            A list of sample IDs for which to aggregate the class distributions.
        sample_id_to_annotations:
            A dictionary mapping sample IDs to a list of their annotations.
        target_annotation_ids:
            A list of annotation label IDs that are considered for the distribution.
            The order of these IDs determines the order of the columns in the output.

    Returns:
        A numpy array of shape (n_samples, n_labels) where n_samples is the
        number of input samples and n_labels is the number of target annotation
        labels. Each row in the array represents the class distribution for a
        sample, where the values are the counts of each target annotation label.
    """
    n_samples = len(input_sample_ids)
    n_labels = len(target_annotation_ids)

    class_distributions = np.zeros((n_samples, n_labels), dtype=np.float32)
    annotation_id_to_idx = {
        annotation_id: j for j, annotation_id in enumerate(target_annotation_ids)
    }
    for i, sample_id in enumerate(input_sample_ids):
        for annotation in sample_id_to_annotations[sample_id]:
            label_idx = annotation_id_to_idx.get(annotation.annotation_label_id)
            if label_idx is not None:
                class_distributions[i, label_idx] += 1

    return class_distributions


def _get_class_balancing_data(
    strat: AnnotationClassBalancingStrategy,
    annotations: Sequence[AnnotationBaseTable],
    input_sample_ids: Sequence[UUID],
    sample_id_to_annotations: Mapping[UUID, Sequence[AnnotationBaseTable]],
) -> tuple[NDArray[np.float32], list[float]]:
    """Helper function to get class balancing data."""
    if strat.distribution == "uniform":
        target_keys_set = {a.annotation_label_id for a in annotations}
        target_keys = list(target_keys_set)
        target_values = [1.0 / len(target_keys)] * len(target_keys)
    elif strat.distribution == "input":
        # Count the number of times each label appears in the input
        input_label_count = Counter(a.annotation_label_id for a in annotations)
        target_keys, target_values = (
            list(input_label_count.keys()),
            list(input_label_count.values()),
        )
    elif isinstance(strat.distribution, dict):
        target_keys, target_values = (
            list(strat.distribution.keys()),
            list(strat.distribution.values()),
        )
    else:
        raise ValueError(f"Unknown distribution type: {type(strat.distribution)}")

    class_distributions = _aggregate_class_distributions(
        input_sample_ids=input_sample_ids,
        sample_id_to_annotations=sample_id_to_annotations,
        target_annotation_ids=target_keys,
    )
    return class_distributions, target_values


def select_via_database(
    session: Session, config: SelectionConfig, input_sample_ids: list[UUID]
) -> None:
    """Run selection using the provided candidate sample ids.

    First resolves the selection config to concrete database values.
    Then calls Mundig to run the selection with pure values.
    Finally creates a tag for the selected set.
    """
    # Check if the tag name is already used
    existing_tag = tag_resolver.get_by_name(
        session=session,
        tag_name=config.selection_result_tag_name,
        dataset_id=config.dataset_id,
    )
    if existing_tag:
        msg = (
            f"Tag with name {config.selection_result_tag_name} already exists in the "
            f"dataset {config.dataset_id}. Please use a different tag name."
        )
        raise ValueError(msg)

    n_samples_to_select = min(config.n_samples_to_select, len(input_sample_ids))
    if n_samples_to_select == 0:
        print("No samples available for selection.")
        return

    mundig = Mundig()
    for strat in config.strategies:
        if isinstance(strat, EmbeddingDiversityStrategy):
            embedding_model_id = embedding_model_resolver.get_by_name(
                session=session,
                dataset_id=config.dataset_id,
                embedding_model_name=strat.embedding_model_name,
            ).embedding_model_id
            embedding_tables = sample_embedding_resolver.get_by_sample_ids(
                session=session,
                sample_ids=input_sample_ids,
                embedding_model_id=embedding_model_id,
            )
            embeddings = [e.embedding for e in embedding_tables]
            mundig.add_diversity(embeddings=embeddings, strength=strat.strength)
        elif isinstance(strat, MetadataWeightingStrategy):
            key = strat.metadata_key
            weights = []
            for sample_id in input_sample_ids:
                weight = metadata_resolver.get_value_for_sample(session, sample_id, key)
                if not isinstance(weight, (float, int)):
                    raise ValueError(
                        f"Metadata {key} is not a number, only numbers can be used as weights"
                    )
                weights.append(float(weight))
            mundig.add_weighting(weights=weights, strength=strat.strength)
        elif isinstance(strat, AnnotationClassBalancingStrategy):
            annotations = annotation_resolver.get_all(
                session=session,
                filters=AnnotationsFilter(sample_ids=input_sample_ids),
            ).annotations
            sample_id_to_annotations = defaultdict(list)
            for annotation in annotations:
                sample_id_to_annotations[annotation.parent_sample_id].append(annotation)

            class_distributions, target_values = _get_class_balancing_data(
                strat=strat,
                annotations=annotations,
                input_sample_ids=input_sample_ids,
                sample_id_to_annotations=sample_id_to_annotations,
            )
            mundig.add_class_balancing(
                class_distributions=class_distributions,
                target=target_values,
                strength=strat.strength,
            )
        else:
            raise ValueError(f"Selection strategy of type {type(strat)} is unknown.")

    selected_indices = mundig.run(n_samples=n_samples_to_select)
    selected_sample_ids = [input_sample_ids[i] for i in selected_indices]

    datetime_str = datetime.datetime.now(tz=datetime.timezone.utc).isoformat()
    tag_description = f"Selected at {datetime_str} UTC"
    tag = tag_resolver.create(
        session=session,
        tag=TagCreate(
            dataset_id=config.dataset_id,
            name=config.selection_result_tag_name,
            kind="sample",
            description=tag_description,
        ),
    )
    tag_resolver.add_sample_ids_to_tag_id(
        session=session, tag_id=tag.tag_id, sample_ids=selected_sample_ids
    )
