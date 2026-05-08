"""Example of how to evaluate two COCO annotation sets."""

from collections import defaultdict

from environs import Env

import lightly_studio as ls
from lightly_studio import db_manager
from lightly_studio.core.dataset_query import ImageSampleField
from lightly_studio.evaluation.image_dataset_evaluate import ObjectDetectionEvaluationConfig
from lightly_studio.resolvers import (
    evaluation_run_resolver,
    evaluation_sample_metric_resolver,
)

# Read environment variables
env = Env()
env.read_env()

# Cleanup an existing database
db_manager.connect(cleanup_existing=True)

# Define data paths
images_path = (
    "D:/01_work/model_eval/interface/add_together/lightly-studio/lightly_studio/"
    "dataset_examples/coco_subset_128_images/images"
)  # env.path("EXAMPLES_COCO_IMAGES_PATH", "/path/to/your/images")
gt_annotations_json = env.path("EXAMPLES_COCO_JSON_PATH", "/path/to/your/gt.json")
pred_annotations_json = env.path("EXAMPLES_PRED_ANNOTATIONS_JSON", "/path/to/your/pred.json")
iou_threshold = env.float("EXAMPLES_IOU_THRESHOLD", 0.5)
classwise = env.bool("EXAMPLES_CLASSWISE", True)

# Create dataset and add images
dataset = ls.ImageDataset.create(name="evaluation_example_dataset")
dataset.add_images_from_path(path=images_path)

# Add two different annotation collections from COCO
dataset.add_annotations_from_coco(
    annotations_json=gt_annotations_json,
    images_root=images_path,
    name="gt",
)
dataset.add_annotations_from_coco(
    annotations_json=pred_annotations_json,
    images_root=images_path,
    name="pred",
)

# Tag first 10 samples and build a query that only selects tagged samples.
tag_name = "evaluated_samples"
dataset.query()[:10].add_tag(tag_name)
evaluation_query = dataset.query().match(ImageSampleField.tags.contains(tag_name))

# Run evaluation
evaluation_name_1 = "evaluation-example-tagged-samples"
dataset.evaluate(query=evaluation_query).object_detection(
    name=evaluation_name_1,
    gt_collection_name="gt",
    pred_collection_name="pred",
    config=ObjectDetectionEvaluationConfig(
        iou_threshold=iou_threshold,
        classwise=classwise,
    ),
)
evaluation_name = "evaluation-example-all-samples"
dataset.evaluate().object_detection(
    name=evaluation_name,
    gt_collection_name="gt",
    pred_collection_name="pred",
    config=ObjectDetectionEvaluationConfig(
        iou_threshold=iou_threshold,
        classwise=classwise,
    ),
)

# Fetch and print metric bounds for the newly created evaluation run.
evaluation_runs = evaluation_run_resolver.get_all_by_dataset_id(
    session=dataset.session,
    dataset_id=dataset.dataset_id,
)
latest_run = next((run for run in evaluation_runs if run.name == evaluation_name_1), None)
if latest_run is None:
    raise ValueError(f"Could not resolve evaluation run: {evaluation_name_1}")

metric_list = evaluation_sample_metric_resolver.get_metric_list_by_evaluation_run_id(
    session=dataset.session,
    evaluation_run_id=latest_run.id,
)
print("\n=== Evaluation Metric Bounds ===")
for metric in sorted(metric_list, key=lambda x: x.metric_name):
    print(f"- {metric.metric_name}: min={metric.min_value:.2f}, max={metric.max_value:.2f}")

sample_metrics = evaluation_sample_metric_resolver.get_all_by_evaluation_run_id(
    session=dataset.session,
    evaluation_run_id=latest_run.id,
)

metrics_by_sample: dict[str, dict[str, float]] = defaultdict(dict)
for row in sample_metrics:
    metrics_by_sample[str(row.sample_id)][row.metric_name] = row.value

print("\n=== Per-Sample Metrics ===")
for sample_id in sorted(metrics_by_sample):
    sample_values = metrics_by_sample[sample_id]
    tp = sample_values.get("tp", 0.0)
    fp = sample_values.get("fp", 0.0)
    fn = sample_values.get("fn", 0.0)
    print(f"- sample_id={sample_id} -> tp={tp:.0f}, fp={fp:.0f}, fn={fn:.0f}")

ls.start_gui()
