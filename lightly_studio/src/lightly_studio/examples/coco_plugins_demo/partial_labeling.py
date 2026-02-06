"""Utilities for creating a partially labeled dataset."""

from __future__ import annotations

import random

import lightly_studio as ls
from lightly_studio.resolvers import annotation_resolver

PARTIAL_LABEL_RATIO = 0.5
PARTIAL_LABEL_SEED = 42
TAG_LABELED = "labeled"
TAG_UNLABELED = "unlabeled"


def make_partially_labeled_dataset(
    dataset: ls.ImageDataset,
    ratio: float = PARTIAL_LABEL_RATIO,
    seed: int = PARTIAL_LABEL_SEED,
) -> None:
    """Create a partially labeled dataset by deleting annotations for some samples.

    Args:
        dataset: Dataset to modify in-place.
        ratio: Fraction of annotated samples to convert into unlabeled samples.
        seed: Random seed for reproducible sampling.
    """
    if ratio < 0.0 or ratio > 1.0:
        raise ValueError("ratio must be between 0 and 1")

    samples = list(dataset)
    samples_with_annotations = [sample for sample in samples if sample.annotations]
    samples_without_annotations = [sample for sample in samples if not sample.annotations]

    rng = random.Random(seed)
    num_unlabeled = int(len(samples_with_annotations) * ratio)
    unlabeled_samples = rng.sample(samples_with_annotations, num_unlabeled)
    unlabeled_sample_ids = {sample.sample_id for sample in unlabeled_samples}
    unlabeled_sample_ids.update(sample.sample_id for sample in samples_without_annotations)

    for sample in samples:
        if sample.sample_id in unlabeled_sample_ids:
            annotation_ids = [
                annotation.annotation_base.sample_id for annotation in sample.annotations
            ]
            for annotation_id in annotation_ids:
                annotation_resolver.delete_annotation(
                    session=dataset.session,
                    annotation_id=annotation_id,
                )
            sample.add_tag(TAG_UNLABELED)
        else:
            sample.add_tag(TAG_LABELED)
