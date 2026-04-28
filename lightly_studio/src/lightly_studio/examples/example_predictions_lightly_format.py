"""Example: loading ground-truth and predictions, then computing evaluation metrics.

This script answers the open design questions for the Model Evaluation feature:

Q1 - How do predictions enter the DB?
    Via dataset.add_predictions_from_lightly(). It assumes images are already in
    the dataset and only creates annotation records, assigning them to a named
    AnnotationCollection (is_ground_truth=False). Confidence scores are read from
    the ``score`` field in each Lightly annotation JSON file.

Q2 - Annotation collection creation UI needed?
    No. Collections are created programmatically here. The GUI only reads and
    evaluates existing collections.

Q3 - Tag filtering logic?
    Tags define subsets. Evaluation is computed once per tag ("train", "test", …)
    plus once for the full dataset ("all"). Each tag becomes one column in the
    results table — one metric run per tag, no AND/OR logic.

Q4 - Does pycocotools need to be added as a dependency?
    Yes — dataset.evaluate() uses pycocotools COCOeval internally.
    It is added to lightly_studio/pyproject.toml.
"""

from environs import Env

import lightly_studio as ls
from lightly_studio import db_manager

env = Env()
env.read_env()

gt_folder_train = "/Users/jonaswurst/Lightly/dataset_examples/coco_subset_128_images/images"
gt_json = "/Users/jonaswurst/Lightly/dataset_examples/coco_subset_128_images/instances_train2017.json"
model_1_folder = "/Users/jonaswurst/Lightly/dataset_examples/coco_subset_128_images/predictions"
model_2_folder = "/Users/jonaswurst/Lightly/dataset_examples/coco_subset_128_images/predictions"

db_manager.connect(cleanup_existing=True)

# ---------------------------------------------------------------------------
# 1. Load images with ground-truth annotations.
#
# `split` creates a tag of that name on every loaded sample.
# Tags define the subsets used during evaluation (one column per tag + "all").
# `annotation_collection` is the name of the AnnotationCollection that groups
# these annotations. Passing the same name twice accumulates annotations from
# both splits into a single GT collection.
# ---------------------------------------------------------------------------
dataset = ls.ImageDataset.create()

dataset.add_samples_from_coco(
    annotations_json=gt_json,
    images_path=gt_folder_train,
    annotation_collection="ground_truth",
    is_ground_truth=True,
)


# ---------------------------------------------------------------------------
# 2. Load predictions from two models.
#
# add_predictions_from_lightly differs from add_samples_from_lightly in that
# it does NOT create new image records — images must already exist. It reads
# confidence scores from the ``score`` field in each Lightly annotation file
# and assigns all annotations to a new AnnotationCollection (is_ground_truth=False).
# Images not found in the dataset are skipped with a warning.
# ---------------------------------------------------------------------------
dataset.add_predictions_from_lightly(
    input_folder=model_1_folder,
    collection_name="YOLOv8-n epoch 50",
)
dataset.add_predictions_from_lightly(
    input_folder=model_2_folder,
    collection_name="Faster RCNN baseline",
)

# ---------------------------------------------------------------------------
# 3. Compute evaluation metrics.
#
# For each prediction collection × subset combination, COCO metrics are
# computed via pycocotools. Subsets = "all" + one entry per tag on the
# dataset ("train", "test" in this example).
#
# Results are persisted as an EvaluationResult record and returned here.
# ---------------------------------------------------------------------------
result = dataset.evaluate(
    gt_collection="ground_truth",
    prediction_collections=["YOLOv8-n epoch 50", "Faster RCNN baseline"],
    iou_threshold=0.5,
    confidence_threshold=0.0,
)

# ---------------------------------------------------------------------------
# 4. Inspect results.
#
# result.metrics structure:
#   dict[prediction_collection_name → dict[subset_name → dict[metric → float]]]
#
# subset_name is "all" or a tag name ("train", "test").
# Metrics: precision, recall, f1, mAP, avg_confidence.
#
# This structure drives both pivot modes in the tabular GUI view:
#   - Fix subset  → iterate over prediction_collections (columns = models)
#   - Fix model   → iterate over subsets          (columns = tags)
# ---------------------------------------------------------------------------
for model_name, subsets in result.metrics.items():
    for subset_name, metrics in subsets.items():
        print(
            f"{model_name:30s} | {subset_name:8s} | "
            f"mAP={metrics['mAP']:.3f}  "
            f"P={metrics['precision']:.3f}  "
            f"R={metrics['recall']:.3f}  "
            f"F1={metrics['f1']:.3f}  "
            f"conf={metrics['avg_confidence']:.3f}"
        )

ls.start_gui()
