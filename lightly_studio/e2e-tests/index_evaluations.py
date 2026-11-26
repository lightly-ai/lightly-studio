"""End-to-end demonstration of object detection evaluation and the UI."""

import e2e_fixture

import lightly_studio as ls
from lightly_studio.core.dataset_query import ImageSampleField
from lightly_studio.evaluation.image_dataset_evaluate import ObjectDetectionEvaluationConfig

IMAGES_PATH = "datasets/coco_subset_128_images/images"
ANNOTATIONS_JSON = "datasets/coco_subset_128_images/instances_train2017.json"

DATASET_NAME = "evaluation_example_dataset"
GT_ANNOTATION_SOURCE = "COCO annotations"
PRED_ANNOTATION_SOURCE = "YOLOv8-m inferences"
QUERY_GT_ANNOTATION_SOURCE = "Query filter ground truth"
QUERY_PRED_ANNOTATION_SOURCE = "Query filter predictions"

EVALUATED_SAMPLES_TAG = "evaluated_samples"
TAGGED_SAMPLES_EVALUATION_NAME = "evaluation-example-tagged-samples"
ALL_SAMPLES_EVALUATION_NAME = "evaluation-example-all-samples"


def seed() -> None:
    """Create the evaluations E2E fixture."""
    dataset = ls.ImageDataset.create(name=DATASET_NAME)
    dataset.add_images_from_path(path=IMAGES_PATH)
    _add_annotations(dataset=dataset)
    _add_tags(dataset=dataset)
    _create_evaluations(dataset=dataset)


def _add_annotations(dataset: ls.ImageDataset) -> None:
    for annotation_source in (GT_ANNOTATION_SOURCE, PRED_ANNOTATION_SOURCE):
        dataset.add_annotations_from_coco(
            annotations_json=ANNOTATIONS_JSON,
            images_root=IMAGES_PATH,
            annotation_source=annotation_source,
        )

    # Keep query filter metrics independent of annotation edits in the stale-warning test.
    for annotation_source in (QUERY_GT_ANNOTATION_SOURCE, QUERY_PRED_ANNOTATION_SOURCE):
        dataset.add_annotations_from_coco(
            annotations_json=ANNOTATIONS_JSON,
            images_root=IMAGES_PATH,
            annotation_source=annotation_source,
            embed_annotations=False,
        )


def _add_tags(dataset: ls.ImageDataset) -> None:
    dataset.query()[:10].add_tag(tag_name=EVALUATED_SAMPLES_TAG)
    # Tags for the distribution panel comparison. The first two overlap on [16:32].
    dataset.query()[:32].add_tag(tag_name="distribution_reviewed")
    dataset.query()[16:48].add_tag(tag_name="distribution_priority")
    dataset.query()[:0].add_tag(tag_name="distribution_empty")


def _create_evaluations(dataset: ls.ImageDataset) -> None:
    evaluation_config = ObjectDetectionEvaluationConfig(
        iou_threshold=0.5,
        classwise=True,
    )

    tagged_evaluation_query = dataset.query().match(
        ImageSampleField.tags.contains(EVALUATED_SAMPLES_TAG)
    )
    dataset.evaluate(query=tagged_evaluation_query).object_detection(
        name=TAGGED_SAMPLES_EVALUATION_NAME,
        gt_annotation_source=QUERY_GT_ANNOTATION_SOURCE,
        pred_annotation_source=QUERY_PRED_ANNOTATION_SOURCE,
        config=evaluation_config,
    )

    dataset.evaluate().object_detection(
        name=ALL_SAMPLES_EVALUATION_NAME,
        gt_annotation_source=GT_ANNOTATION_SOURCE,
        pred_annotation_source=PRED_ANNOTATION_SOURCE,
        config=evaluation_config,
    )


if __name__ == "__main__":
    e2e_fixture.run(seed=seed, default_db_file="lightly_studio.db")
