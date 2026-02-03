"""Example of how to use LightlyStudio with LightlyTrain plugins to create an end-to-end workflow for training and inference on a partially labeled dataset.

First, we create a partially labeled dataset, by deleting half the annotations randomly.
The sets are tagged as "labeled" and "unlabeled".

Then two plugins are added

1. Running Training directly from Studio via a plugin. This is fully faked and returns directly. It uses a tag as training set, which includes labels.
2. Running Inference directly from Studio via a plugin. It uses the pretrained checkpoint and runs inference only on the unlabeled images, i.e. a different tag.

# Hint for development: You might need to install newer packages of huggingface_hub torch or torchvision via pip install --upgrade to avoid runtime or import errors.
"""

import random

from environs import Env

import lightly_studio as ls
from lightly_studio import db_manager
from lightly_studio.examples.lightly_train_inference_operator import (
    LightlyTrainObjectDetectionInferenceOperator,
)
from lightly_studio.examples.lightly_train_training_operator import (
    LightlyTrainObjectDetectionTrainingOperator,
)
from lightly_studio.plugins.operator_registry import operator_registry
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


# Read environment variables
env = Env()
env.read_env()

# Cleanup an existing database
db_manager.connect(cleanup_existing=True)

# Define data paths
annotations_json = env.path("EXAMPLES_COCO_JSON_PATH", "/path/to/your/dataset/annotations.json")
images_path = env.path("EXAMPLES_COCO_IMAGES_PATH", "/path/to/your/dataset")

# Create the dataset
dataset = ls.ImageDataset.create()
dataset.add_samples_from_coco(
    annotations_json=annotations_json,
    images_path=images_path,
    annotation_type=ls.AnnotationType.INSTANCE_SEGMENTATION,
)

make_partially_labeled_dataset(
    dataset=dataset,
    ratio=PARTIAL_LABEL_RATIO,
    seed=PARTIAL_LABEL_SEED,
)

operator_registry.register(operator=LightlyTrainObjectDetectionTrainingOperator())
operator_registry.register(operator=LightlyTrainObjectDetectionInferenceOperator())

ls.start_gui()
