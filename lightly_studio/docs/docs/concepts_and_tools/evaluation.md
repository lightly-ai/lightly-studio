# Evaluation

Evaluation runs let you compare model predictions against ground truth
[annotations](annotations.md) and surface per-sample quality metrics in LightlyStudio. Supported
task types are object detection and classification.

## Evaluation in the GUI

PLACEHOLDER GIF OR VIDEO 

Evaluation results are accessible in the **Evaluation** panel of the GUI once a run has been created via the [Python API](#evaluation-in-python). Select an evaluation run in the **Evaluation** panel to inspect its configuration and confusion matrix. Then use the sample grid to drill into the underlying samples:

- Sort by `fp`, `fn`, or `tp` for object detection runs.
- Sort by `disagreement` for classification runs.
- Sort by `mIoU` for semantic segmentation.
- Filter to the affected classes and inspect the hardest samples in detail view.

!!! hint "Reading the confusion matrix"

    - Strong diagonal values indicate correct predictions.
    - Large off-diagonal values indicate systematic class confusion.
    - Use those cells to decide which samples to inspect next in the grid.

## Evaluation in Python

### Creating an evaluation run

An evaluation run requires two annotation sources: one holding ground truth labels and one
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
        gt_source_name="ground_truth",
        pred_source_name="predictions",
        config=config,
    )

    print(f"Evaluated {result.sample_count} samples")
    print(f"GT annotations: {result.gt_annotation_count}")
    print(f"Prediction annotations: {result.pred_annotation_count}")
    ```

    Matching between predicted and ground truth boxes is based on intersection over union (IoU).
    The `iou_threshold` in the configuration defines the minimum IoU required for a prediction and
    a ground truth box to count as a match. Matched pairs contribute to true positives (`tp`),
    while unmatched predictions and unmatched ground truth boxes contribute to false positives
    (`fp`) and false negatives (`fn`).

    The `classwise` setting controls whether matching is restricted to boxes with the same class
    label. With `classwise=True`, a predicted `dog` box can only match a ground truth `dog` box.
    Disable `classwise` if you want cross-class matches to populate the confusion matrix
    off-diagonal, for example when a predicted `dog` is matched against a ground truth `cat`.

    The resulting per-sample metrics are stored as `tp`, `fp`, and `fn`, which means you can sort
    samples by the total number of true positives, false positives, or false negatives.

=== "Classification"

    ```python
    result = dataset.evaluate().classification(
        name="my-cls-eval",
        gt_source_name="ground_truth",
        pred_source_name="predictions",
    )

    print(f"Evaluated {result.sample_count} samples")
    ```

    Classification evaluation populates the confusion matrix directly from the ground truth and
    predicted labels.

    Per-sample metric stored: `disagreement` in `[0, 1]`. It is calculated as `1 - confidence`
    when the labels match, and as `confidence` when the labels do not match. Higher values
    indicate stronger disagreement between the ground truth and the prediction.

    You can sort samples by `disagreement` to inspect the most uncertain correct predictions or the
    most confident wrong predictions first.

### Evaluating a subset of samples

Pass a [`DatasetQuery`](../api/dataset_query.md) to `evaluate()` to restrict the run to a specific
set of samples — for example, a tagged validation split:

```python
from lightly_studio.core.dataset_query import ImageSampleField

val_query = dataset.query().match(ImageSampleField.tags.contains("val"))

result = dataset.evaluate(query=val_query).object_detection(
    name="val-eval",
    gt_source_name="ground_truth",
    pred_source_name="predictions",
)
```

Only samples that appear in both annotation sources **and** in the query are included. Samples
missing from either source are silently skipped.

See [Evaluation API Reference](../api/evaluation.md) for the full API surface.
