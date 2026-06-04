"""Example script demonstrating semantic segmentation model evaluation capabilities."""

import json
from collections import defaultdict
from pathlib import Path
from time import perf_counter
from uuid import UUID

from environs import Env

import lightly_studio as ls
from lightly_studio import db_manager
from lightly_studio.core.dataset_query import ImageSampleField
from lightly_studio.core.image.image_dataset import ImageDataset
from lightly_studio.models.evaluation_run import EvaluationRunTable
from lightly_studio.resolvers import (
    evaluation_run_resolver,
    evaluation_sample_metric_resolver,
)

DATASET_NAME = "sem_segmentation_evaluation_example_dataset"
GT_ANNOTATION_SOURCE = "gt"
PRED_ANNOTATION_SOURCE = "pred"

TAGGED_SAMPLES_EVALUATION_NAME = "sem-segmentation-evaluation-tagged-samples"
ALL_SAMPLES_EVALUATION_NAME = "sem-segmentation-evaluation-all-samples"

TAGGED_SAMPLE_COUNT = 3


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


def print_evaluation_metrics(
    dataset: ImageDataset,
    name: str,
) -> None:
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

    print_per_sample_metrics(
        dataset=dataset,
        evaluation_run=evaluation_run,
    )


def print_per_sample_metrics(
    dataset: ImageDataset,
    evaluation_run: EvaluationRunTable,
) -> None:
    """Print miou scores per sample."""
    sample_metrics = evaluation_sample_metric_resolver.get_all_by_evaluation_run_id(
        session=dataset.session,
        evaluation_run_id=evaluation_run.id,
    )

    metrics_by_sample: dict[UUID, dict[str, float]] = defaultdict(dict)
    for row in sample_metrics:
        metrics_by_sample[row.sample_id][row.metric_name] = row.value

    print("\n=== Per-Sample Metrics ===")
    for sample_id in sorted(metrics_by_sample):
        miou = metrics_by_sample[sample_id].get("miou", 0.0)
        print(f"- sample_id={sample_id}: miou={miou:.2f}")


def main() -> None:
    """Run the semantic segmentation evaluation example."""
    # Read environment variables
    env = Env()
    env.read_env()

    # Cleanup an existing database
    db_manager.connect(cleanup_existing=True)

    # Define data paths
    images_path = env.path("EXAMPLES_PASCALVOC_IMAGES_PATH", "/path/to/your/dataset/images")
    gt_masks_path = env.path("EXAMPLES_PASCALVOC_MASKS_PATH", "/path/to/your/dataset/masks")
    pred_masks_path = env.path(
        "EXAMPLES_PASCALVOC_MASKS_PATH_PREDICTIONS", "/path/to/your/dataset/pred_masks"
    )

    # A mapping from class IDs to class names must be provided. We load it from a JSON file,
    # the file is not part of the Pascal VOC format.
    class_id_to_name_path = env.path(
        "EXAMPLES_PASCALVOC_CATEGORIES_JSON_PATH",
        "/path/to/your/dataset/class_id_to_name.json",
    )
    json_dict = json.loads(Path(class_id_to_name_path).read_text())
    class_id_to_name = {int(k): v for k, v in json_dict.items()}

    # Create a dataset and add images and annotations from the Pascal VOC format for ground truth
    # and predictions.
    dataset = ls.ImageDataset.create()
    dataset.add_images_from_path(path=images_path)

    dataset.add_annotations_from_pascal_voc_segmentations(
        images_root=images_path,
        masks_path=gt_masks_path,
        class_id_to_name=class_id_to_name,
        annotation_source=GT_ANNOTATION_SOURCE,
    )
    dataset.add_annotations_from_pascal_voc_segmentations(
        images_root=images_path,
        masks_path=pred_masks_path,
        class_id_to_name=class_id_to_name,
        annotation_source=PRED_ANNOTATION_SOURCE,
    )

    tag_name = "evaluated_samples"
    dataset[:TAGGED_SAMPLE_COUNT].add_tag(tag_name)
    tagged_evaluation_query = dataset.query().match(ImageSampleField.tags.contains(tag_name))

    print("\nEvaluating tagged samples...")
    start_time = perf_counter()
    evaluation_result = dataset.evaluate(query=tagged_evaluation_query).semantic_segmentation(
        name=TAGGED_SAMPLES_EVALUATION_NAME,
        gt_annotation_source=GT_ANNOTATION_SOURCE,
        pred_annotation_source=PRED_ANNOTATION_SOURCE,
    )
    print(
        f"Completed in {perf_counter() - start_time:.2f}s "
        f"using {evaluation_result.sample_count} samples, "
        f"{evaluation_result.gt_annotation_count} GT annotations, and "
        f"{evaluation_result.pred_annotation_count} prediction annotations"
    )
    print_evaluation_metrics(
        dataset=dataset,
        name=TAGGED_SAMPLES_EVALUATION_NAME,
    )

    print("\nEvaluating all annotated samples...")
    start_time = perf_counter()
    evaluation_result = dataset.evaluate().semantic_segmentation(
        name=ALL_SAMPLES_EVALUATION_NAME,
        gt_annotation_source=GT_ANNOTATION_SOURCE,
        pred_annotation_source=PRED_ANNOTATION_SOURCE,
    )
    print(
        f"Completed in {perf_counter() - start_time:.2f}s "
        f"using {evaluation_result.sample_count} samples, "
        f"{evaluation_result.gt_annotation_count} GT annotations, and "
        f"{evaluation_result.pred_annotation_count} prediction annotations"
    )
    print_evaluation_metrics(
        dataset=dataset,
        name=ALL_SAMPLES_EVALUATION_NAME,
    )

    ls.start_gui()


if __name__ == "__main__":
    main()
