# Evaluation

Evaluation runs let you compare model predictions against ground truth
[annotations](annotations.md) and surface per-sample quality metrics in LightlyStudio. Supported
task types are object detection and classification.

## Evaluation in the GUI

PLACEHOLDER GIF OR VIDEO 

Evaluation results are accessible in the **Evaluation** panel of the GUI once a run has been
created via the [Python API](#evaluation-in-python).

Each evaluation run adds per-sample metrics as sortable columns in the sample grid. Use the
**Sort** and **Filter** controls to surface samples with the highest false-positive counts, the
greatest disagreement score, or any other metric.

Select an evaluation run in the **Evaluation** panel to see the configuration for each run. For object detection and classification runs, LightlyStudio also renders a confusion matrix in the **Evaluation** panel that shows how often each ground truth class was matched to each predicted class.

## Evaluation in Python

### Creating an evaluation run

An evaluation run requires two annotation collections: one holding ground truth labels and one
holding model predictions. Use `dataset.evaluate()` to get the evaluation facade and then call the
task-specific method. Both return an [`EvaluationResult`](../api/evaluation.md#evaluationresult)
summary.

=== "Object detection"

    ```python
    from lightly_studio.evaluation.image_dataset_evaluate import ObjectDetectionEvaluationConfig

    config = ObjectDetectionEvaluationConfig(
        iou_threshold=0.5,  # minimum IoU to count a detection as a true positive
        classwise=True,     # match predictions only within the same class label
    )

    result = dataset.evaluate().object_detection(
        name="my-od-eval",
        gt_collection_name="ground_truth",
        pred_collection_name="predictions",
        config=config,
    )

    print(f"Evaluated {result.sample_count} samples")
    print(f"GT annotations: {result.gt_annotation_count}")
    print(f"Prediction annotations: {result.pred_annotation_count}")
    ```

    Per-sample metrics stored: `tp`, `fp`, `fn`.

=== "Classification"

    ```python
    result = dataset.evaluate().classification(
        name="my-cls-eval",
        gt_collection_name="ground_truth",
        pred_collection_name="predictions",
    )

    print(f"Evaluated {result.sample_count} samples")
    ```

    Per-sample metric stored: `disagreement` in `[0, 1]`. Higher values indicate stronger
    disagreement between the ground truth and the prediction.

### Evaluating a subset of samples

Pass a [`DatasetQuery`](../api/dataset_query.md) to `evaluate()` to restrict the run to a specific
set of samples — for example, a tagged validation split:

```python
from lightly_studio.core.dataset_query import ImageSampleField

val_query = dataset.query().match(ImageSampleField.tags.contains("val"))

result = dataset.evaluate(query=val_query).object_detection(
    name="val-eval",
    gt_collection_name="ground_truth",
    pred_collection_name="predictions",
)
```

Only samples that appear in both annotation collections **and** in the query are included. Samples
missing from either collection are silently skipped.

See [Evaluation API Reference](../api/evaluation.md) for the full API surface.
