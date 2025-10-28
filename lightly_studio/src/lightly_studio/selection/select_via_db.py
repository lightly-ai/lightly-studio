"""Database selection functions for the selection process."""

from __future__ import annotations

import datetime
from collections import defaultdict
from uuid import UUID

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
    input_sample_ids: list[UUID],
    sample_id_to_annotations: dict[UUID, list[AnnotationBaseTable]],
    target: dict[UUID, float],
) -> list[list[int]]:
    class_distributions = []
    for sample_id in input_sample_ids:
        annotations_for_sample = annotations_by_sample_id[sample_id]
        # For each target label, count the number of annotations
        counts_for_sample: dict[UUID, int] = defaultdict(int)
        for annotation in annotations_for_sample:
            counts_for_sample[annotation.annotation_label_id] += 1

        counts_as_list = []
        for label_id in target:
            counts_as_list.append(counts_for_sample.get(label_id, 0))
        class_distributions.append(counts_as_list)
    return class_distributions


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
            annotations_by_sample_id = defaultdict(list)
            for annotation in annotations:
                annotations_by_sample_id[annotation.sample_id].append(annotation)

            class_distributions = _aggregate_class_distributions(
                input_sample_ids=input_sample_ids,
                annotations_by_sample_id=annotations_by_sample_id,
                target=strat.target,
            )
            mundig.add_class_balancing(
                class_distributions=class_distributions,
                target=list(strat.target.values()),
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
