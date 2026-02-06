"""LightyStudio example with LightlyTrain plugins for partially labeled COCO dataset.

Example of how to use LightlyStudio with LightlyTrain plugins to create an end-to-end
 workflow for training and inference on a partially labeled dataset.

First, creates a partially labeled dataset, by deleting half the annotations randomly.
The sets are tagged as "labeled" and "unlabeled".

Then two plugins are added

1. Running Training directly from Studio via a plugin. It uses a tag as training set, which
 includes labels.
2. Running Inference directly from Studio via a plugin. It uses the pretrained checkpoint
 and runs inference only on the unlabeled images, i.e. a different tag.

 This requires LightlyTrain to be installed via `pip install lightly-train`.

Hint for development: You might need to install newer packages of `huggingface_hub`, `torch`,
or `torchvision` via `pip install --upgrade` to avoid runtime or import errors.
"""

from environs import Env

import lightly_studio as ls
from lightly_studio import db_manager
from lightly_studio.examples.coco_plugins_demo.lightly_train_inference_operator import (
    LightlyTrainObjectDetectionInferenceOperator,
)
from lightly_studio.examples.coco_plugins_demo.lightly_train_training_operator import (
    LightlyTrainObjectDetectionTrainingOperator,
)
from lightly_studio.examples.coco_plugins_demo.partial_labeling import (
    PARTIAL_LABEL_RATIO,
    PARTIAL_LABEL_SEED,
    make_partially_labeled_dataset,
)
from lightly_studio.plugins.operator_registry import operator_registry

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
