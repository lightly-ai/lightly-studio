"""Example script demonstrating classification model evaluation capabilities."""

import random
from collections import defaultdict
from time import perf_counter
from uuid import UUID

from environs import Env

import lightly_studio as ls
from lightly_studio import db_manager
from lightly_studio.core.annotation.annotation_create import CreateClassification
from lightly_studio.core.dataset_query import ImageSampleField
from lightly_studio.core.image.image_dataset import ImageDataset
from lightly_studio.models.evaluation_run import EvaluationRunTable
from lightly_studio.resolvers import (
    annotation_resolver,
    evaluation_run_resolver,
    evaluation_sample_metric_resolver,
)

DATASET_NAME = "classification_evaluation_example_dataset"
GT_ANNOTATION_SOURCE = "gt"
PRED_ANNOTATION_SOURCE = "pred"

TAGGED_SAMPLES_EVALUATION_NAME = "cls-evaluation-tagged-samples"
ALL_SAMPLES_EVALUATION_NAME = "cls-evaluation-all-samples"

TAGGED_SAMPLE_COUNT = 10
<<<<<<< HEAD
CLASS_NAMES = ("cat very long name", "dog", "bird")
=======
CLASS_NAMES = ("cat", "dog", "bird")
>>>>>>> origin/main
RANDOM_SEED = 42


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


def create_classification_annotations(dataset: ImageDataset) -> None:
    """Create GT and prediction classification annotations."""
    gt_annotations = []
    pred_annotations = []
    rng = random.Random(RANDOM_SEED)

    for sample in dataset:
        gt_label = rng.choice(CLASS_NAMES)
        pred_label = rng.choice(CLASS_NAMES)
        pred_confidence = rng.uniform(0.5, 1.0)

        gt_annotations.append(
            CreateClassification(class_name=gt_label).to_annotation_create(
                session=dataset.session,
                dataset_id=dataset.dataset_id,
                parent_sample_id=sample.sample_id,
            )
        )
        pred_annotations.append(
            CreateClassification(
                class_name=pred_label,
                confidence=pred_confidence,
            ).to_annotation_create(
                session=dataset.session,
                dataset_id=dataset.dataset_id,
                parent_sample_id=sample.sample_id,
            )
        )

    annotation_resolver.create_many(
        session=dataset.session,
        parent_collection_id=dataset.collection_id,
        annotations=gt_annotations,
        collection_name=GT_ANNOTATION_SOURCE,
    )
    annotation_resolver.create_many(
        session=dataset.session,
        parent_collection_id=dataset.collection_id,
        annotations=pred_annotations,
        collection_name=PRED_ANNOTATION_SOURCE,
    )


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
    """Print disagreement scores per sample."""
    sample_metrics = evaluation_sample_metric_resolver.get_all_by_evaluation_run_id(
        session=dataset.session,
        evaluation_run_id=evaluation_run.id,
    )

    metrics_by_sample: dict[UUID, dict[str, float]] = defaultdict(dict)
    for row in sample_metrics:
        metrics_by_sample[row.sample_id][row.metric_name] = row.value

    print("\n=== Per-Sample Metrics ===")
    for sample_id in sorted(metrics_by_sample):
        disagreement = metrics_by_sample[sample_id].get("disagreement", 0.0)
        print(f"- sample_id={sample_id}: disagreement={disagreement:.2f}")


def main() -> None:
    """Run the classification evaluation example."""
    env = Env()
    env.read_env()

    db_manager.connect(cleanup_existing=True)

    images_path = env.path("EXAMPLES_COCO_IMAGES_PATH", "/path/to/your/images")

    dataset = ImageDataset.create(name=DATASET_NAME)
    dataset.add_images_from_path(path=images_path)
    create_classification_annotations(dataset=dataset)

    tag_name = "evaluated_samples"
    dataset[:TAGGED_SAMPLE_COUNT].add_tag(tag_name)
    tagged_evaluation_query = dataset.query().match(ImageSampleField.tags.contains(tag_name))

    print("\nEvaluating tagged samples...")
    start_time = perf_counter()
    evaluation_result = dataset.evaluate(query=tagged_evaluation_query).classification(
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
    evaluation_result = dataset.evaluate().classification(
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
