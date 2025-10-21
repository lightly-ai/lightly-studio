"""Database selection functions for the selection process."""

from __future__ import annotations

import datetime
from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.tag import TagCreate
from lightly_studio.resolvers import (
    embedding_model_resolver,
    metadata_resolver,
    sample_embedding_resolver,
    tag_resolver,
)
from lightly_studio.selection.mundig import Mundig
from lightly_studio.selection.selection_config import (
    EmbeddingDiversityStrategy,
    MetadataWeightingStrategy,
    SelectionConfig,
)


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
            mundig.add_weighting(weights, strength=strat.strength)
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
