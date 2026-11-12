"""End-to-end demonstration of object detection evaluation and the UI."""

import lightly_studio as ls
from lightly_studio.core.dataset_query import ImageSampleField
from lightly_studio.database import db_manager
from lightly_studio.evaluation.image_dataset_evaluate import ObjectDetectionEvaluationConfig

IMAGES_PATH = "datasets/coco_subset_128_images/images"
ANNOTATIONS_JSON = "datasets/coco_subset_128_images/instances_train2017.json"

DATASET_NAME = "evaluation_example_dataset"
GT_ANNOTATION_SOURCE = "COCO annotations"
PRED_ANNOTATION_SOURCE = "YOLOv8-m inferences"
QUERY_GT_ANNOTATION_SOURCE = "Query filter ground truth"
QUERY_PRED_ANNOTATION_SOURCE = "Query filter predictions"

TAGGED_SAMPLES_EVALUATION_NAME = "evaluation-example-tagged-samples"
ALL_SAMPLES_EVALUATION_NAME = "evaluation-example-all-samples"

# Cleanup an existing database
db_manager.connect(db_file="lightly_studio.db", cleanup_existing=True)

# Create dataset and add images
dataset = ls.ImageDataset.create(name=DATASET_NAME)
dataset.add_images_from_path(path=IMAGES_PATH)

# Add predictions from two different annotation sources.
dataset.add_annotations_from_coco(
    annotations_json=ANNOTATIONS_JSON,
    images_root=IMAGES_PATH,
    annotation_source=GT_ANNOTATION_SOURCE,
)
dataset.add_annotations_from_coco(
    annotations_json=ANNOTATIONS_JSON,
    images_root=IMAGES_PATH,
    annotation_source=PRED_ANNOTATION_SOURCE,
)

# Keep query filter metrics independent of annotation edits in the stale-warning test.
for annotation_source in (QUERY_GT_ANNOTATION_SOURCE, QUERY_PRED_ANNOTATION_SOURCE):
    dataset.add_annotations_from_coco(
        annotations_json=ANNOTATIONS_JSON,
        images_root=IMAGES_PATH,
        annotation_source=annotation_source,
        embed_annotations=False,
    )

# Tag a subset of samples to demonstrate evaluating a query
tag_name = "evaluated_samples"
dataset.query()[:10].add_tag(tag_name)
tagged_evaluation_query = dataset.query().match(ImageSampleField.tags.contains(tag_name))

# Tags for the distribution panel comparison. The first two overlap on [16:32].
dataset.query()[:32].add_tag("distribution_reviewed")
dataset.query()[16:48].add_tag("distribution_priority")
dataset.query()[:0].add_tag("distribution_empty")

evaluation_config = ObjectDetectionEvaluationConfig(
    iou_threshold=0.5,
    classwise=True,
)

# Evaluate only the tagged samples
dataset.evaluate(query=tagged_evaluation_query).object_detection(
    name=TAGGED_SAMPLES_EVALUATION_NAME,
    gt_annotation_source=QUERY_GT_ANNOTATION_SOURCE,
    pred_annotation_source=QUERY_PRED_ANNOTATION_SOURCE,
    config=evaluation_config,
)

# Evaluate all samples
dataset.evaluate().object_detection(
    name=ALL_SAMPLES_EVALUATION_NAME,
    gt_annotation_source=GT_ANNOTATION_SOURCE,
    pred_annotation_source=PRED_ANNOTATION_SOURCE,
    config=evaluation_config,
)

ls.start_gui(open_browser=False)
