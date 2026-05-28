"""End-to-end demonstration of object detection evaluation and the UI."""

import lightly_studio as ls
from lightly_studio import db_manager
from lightly_studio.core.dataset_query import ImageSampleField
from lightly_studio.evaluation.image_dataset_evaluate import ObjectDetectionEvaluationConfig

IMAGES_PATH = "dataset_examples/coco_subset_128_images/images"
GT_ANNOTATIONS_JSON = "dataset_examples/coco_subset_128_images/instances_train2017.json"
PRED_ANNOTATIONS_JSON = "dataset_examples/coco_subset_128_images/predictions_train2017.json"

DATASET_NAME = "evaluation_example_dataset"
GT_ANNOTATION_SOURCE = "Ground truth"
PRED_ANNOTATION_SOURCE = "Predictions"

TAGGED_SAMPLES_EVALUATION_NAME = "evaluation-example-tagged-samples"
ALL_SAMPLES_EVALUATION_NAME = "evaluation-example-all-samples"

# Cleanup an existing database
db_manager.connect(db_file="lightly_studio.db", cleanup_existing=True)

# Create dataset and add images
dataset = ls.ImageDataset.create(name=DATASET_NAME)
dataset.add_images_from_path(path=IMAGES_PATH)

# Add ground truth and prediction annotation collections
dataset.add_annotations_from_coco(
    annotations_json=GT_ANNOTATIONS_JSON,
    images_root=IMAGES_PATH,
    annotation_source=GT_ANNOTATION_SOURCE,
)
dataset.add_annotations_from_coco(
    annotations_json=PRED_ANNOTATIONS_JSON,
    images_root=IMAGES_PATH,
    annotation_source=PRED_ANNOTATION_SOURCE,
)

# Tag a subset of samples to demonstrate evaluating a query
tag_name = "evaluated_samples"
dataset.query()[:10].add_tag(tag_name)
tagged_evaluation_query = dataset.query().match(ImageSampleField.tags.contains(tag_name))

evaluation_config = ObjectDetectionEvaluationConfig(
    iou_threshold=0.5,
    classwise=True,
)

# Evaluate only the tagged samples
dataset.evaluate(query=tagged_evaluation_query).object_detection(
    name=TAGGED_SAMPLES_EVALUATION_NAME,
    gt_annotation_source=GT_ANNOTATION_SOURCE,
    pred_annotation_source=PRED_ANNOTATION_SOURCE,
    config=evaluation_config,
)

# Evaluate all samples
dataset.evaluate().object_detection(
    name=ALL_SAMPLES_EVALUATION_NAME,
    gt_annotation_source=GT_ANNOTATION_SOURCE,
    pred_annotation_source=PRED_ANNOTATION_SOURCE,
    config=evaluation_config,
)

ls.start_gui()
