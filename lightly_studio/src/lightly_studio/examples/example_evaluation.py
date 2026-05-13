"""Example script demonstrating model evaluation capabilities."""

from collections import defaultdict
from time import perf_counter

from environs import Env

from lightly_studio import db_manager
from lightly_studio.core.dataset_query import ImageSampleField
from lightly_studio.core.image.image_dataset import ImageDataset
from lightly_studio.evaluation.image_dataset_evaluate import ObjectDetectionEvaluationConfig
from lightly_studio.models.evaluation_run import EvaluationRunTable
from lightly_studio.resolvers import (
    evaluation_run_resolver,
    evaluation_sample_metric_resolver,
)

DATASET_NAME = "evaluation_example_dataset"
GT_COLLECTION_NAME = "gt"
PRED_COLLECTION_NAME = "pred"

TAGGED_SAMPLES_EVALUATION_NAME = "evaluation-example-tagged-samples"
ALL_SAMPLES_EVALUATION_NAME = "evaluation-example-all-samples"


def get_evaluation_run(dataset: ImageDataset, name: str) -> EvaluationRunTable:
    """Return the evaluation run with the given name."""
    evaluation_runs = evaluation_run_resolver.get_all_by_dataset_id(
        session=dataset.session,
        dataset_id=dataset.dataset_id,
    )
    evaluation_run = next((run for run in evaluation_runs if run.name == name), None)
    if evaluation_run is None:
        raise ValueError(f"Could not resolve evaluation run: {name}")
    return evaluation_run


def print_evaluation_metrics(dataset: ImageDataset, name: str) -> None:
    """Print metric bounds and per-sample metrics for an evaluation run."""
    evaluation_run = get_evaluation_run(dataset=dataset, name=name)

    metric_list = evaluation_sample_metric_resolver.get_metric_list_by_evaluation_run_id(
        session=dataset.session,
        evaluation_run_id=evaluation_run.id,
    )
    print(f"\n=== {name} Evaluation ===")
    print("\n=== Metric Bounds ===")
    for metric in sorted(metric_list, key=lambda x: x.metric_name):
        print(f"- {metric.metric_name}: min={metric.min_value:.2f}, max={metric.max_value:.2f}")

    print_per_sample_metrics(dataset=dataset, evaluation_run=evaluation_run)


def print_per_sample_metrics(
    dataset: ImageDataset,
    evaluation_run: EvaluationRunTable,
) -> None:
    """Print true/false positive and false negative counts per sample."""
    sample_metrics = evaluation_sample_metric_resolver.get_all_by_evaluation_run_id(
        session=dataset.session,
        evaluation_run_id=evaluation_run.id,
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


def main() -> None:
    """Run the evaluation example."""
    env = Env()
    env.read_env()

    db_manager.connect(cleanup_existing=True)

    images_path = env.path("EXAMPLES_COCO_IMAGES_PATH", "/path/to/your/images")
    gt_annotations_json = env.path("EXAMPLES_COCO_JSON_PATH", "/path/to/your/gt.json")
    pred_annotations_json = env.path("EXAMPLES_PRED_ANNOTATIONS_JSON", "/path/to/your/pred.json")
    evaluation_config = ObjectDetectionEvaluationConfig(
        iou_threshold=0.5,
        classwise=True,
    )

    dataset = ImageDataset.create(name=DATASET_NAME)
    dataset.add_images_from_path(path=images_path)
    # Add GT annotations
    dataset.add_annotations_from_coco(
        annotations_json=gt_annotations_json,
        images_root=images_path,
        name=GT_COLLECTION_NAME,
    )
    # Add Pred annotations
    dataset.add_annotations_from_coco(
        annotations_json=pred_annotations_json,
        images_root=images_path,
        name=PRED_COLLECTION_NAME,
    )
    # Add tag to tagged samples
    tag_name = "evaluated_samples"
    dataset.query()[:10].add_tag(tag_name)
    # Create query for tagged samples
    tagged_evaluation_query = dataset.query().match(ImageSampleField.tags.contains(tag_name))

    print("\nEvaluating tagged samples...")
    start_time = perf_counter()
    evaluation_result = dataset.evaluate(query=tagged_evaluation_query).object_detection(
        name=TAGGED_SAMPLES_EVALUATION_NAME,
        gt_collection_name=GT_COLLECTION_NAME,
        pred_collection_name=PRED_COLLECTION_NAME,
        config=evaluation_config,
    )
    print(
        f"Completed in {perf_counter() - start_time:.2f}s "
        f"using {evaluation_result.sample_count} samples, "
        f"{evaluation_result.gt_annotation_count} GT annotations, and "
        f"{evaluation_result.pred_annotation_count} prediction annotations"
    )
    print_evaluation_metrics(dataset=dataset, name=TAGGED_SAMPLES_EVALUATION_NAME)

    print("\nEvaluating all samples...")
    start_time = perf_counter()
    evaluation_result = dataset.evaluate().object_detection(
        name=ALL_SAMPLES_EVALUATION_NAME,
        gt_collection_name=GT_COLLECTION_NAME,
        pred_collection_name=PRED_COLLECTION_NAME,
        config=evaluation_config,
    )
    print(
        f"Completed in {perf_counter() - start_time:.2f}s "
        f"using {evaluation_result.sample_count} samples, "
        f"{evaluation_result.gt_annotation_count} GT annotations, and "
        f"{evaluation_result.pred_annotation_count} prediction annotations"
    )
    print_evaluation_metrics(dataset=dataset, name=ALL_SAMPLES_EVALUATION_NAME)


if __name__ == "__main__":
    main()
