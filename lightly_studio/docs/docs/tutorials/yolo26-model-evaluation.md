# Evaluate YOLO26 on your dataset with LightlyStudio

In this tutorial, you learn how to evaluate a YOLO26 model against ground-truth labels, find failure patterns, spot bad labels, and fix or export the samples that need attention.

You will:

- Load images and ground-truth labels in YOLO or COCO format.
- Run YOLO26 predictions with Python or the LightlyStudio plugin.
- Evaluate predictions against ground truth.
- Use metrics, the confusion matrix, and embeddings to find problems.
- Tag issues and export data for your annotation vendor.

## Prerequisites

To follow this tutorial, make sure you have:

- Python 3.10 or newer

## Installation

```bash
pip install lightly-studio ultralytics
```

## Load the dataset in LightlyStudio

Create a Python script, for example `evaluate_yolo26.py`, and add the snippet below. Run it to load the example COCO dataset and its ground-truth labels.

```python title="evaluate_yolo26.py"
import lightly_studio as ls

dataset_path = ls.utils.download_example_dataset(download_dir="dataset_examples")

IMAGE_PATH = f"{dataset_path}/coco_subset_128_images/images"
COCO_JSON = f"{dataset_path}/coco_subset_128_images/instances_train2017.json"

# Resets the local database so the tutorial always starts from a clean project.
# Remove this if you want to keep data from previous runs.
ls.db_manager.connect(cleanup_existing=True)
dataset = ls.ImageDataset.create()

dataset.add_images_from_path(path=IMAGE_PATH)
dataset.add_annotations_from_coco(
    annotations_json=COCO_JSON,
    images_root=IMAGE_PATH,
    annotation_source="ground_truth",
)

# Optional: start the GUI now to inspect the data before continuing.
ls.start_gui()
```

If you want to follow along with your own dataset instead, see [Load an Image Dataset](../dataset_setup/image_dataset.md) for loading YOLO, COCO, and other formats, or the [Quickstart](../index.md#quickstart) for a minimal example.

Run the script once to load the images and labels.

!!! tip
    Call `lightly-studio gui` from the command line instead of `ls.start_gui()` in Python
    to open the GUI without reindexing your dataset.

**Expected result:** 128 images loaded with a `ground_truth` annotation layer.

!!! todo "Media placeholder"
    Add a GIF of LightlyStudio opening with 128 images and a ground-truth annotation layer.

!!! tip
    For a more interesting walkthrough, mislabel a few boxes in Studio before running evaluation (wrong class, shifted box, or missing object). This makes it easier to tell wrong annotations apart from real model failures later on.

## Run YOLO26 predictions

There are two ways to generate predictions. Pick one, or run both and compare.

### Option A: Python

Ultralytics returns detections in its own box format (center `x, y, width, height`). LightlyStudio stores annotations as `CreateObjectDetection` objects with a top-left corner, class name, and confidence. The two functions below bridge that gap: one converts a single box, the other runs the model on every image and saves the predictions as a separate annotation layer.

```python
from ultralytics import YOLO
from lightly_studio.core.annotation import CreateObjectDetection


def yolo_box_to_annotation(box, class_names: dict[int, str]) -> CreateObjectDetection:
    """Convert a single Ultralytics box to a LightlyStudio object-detection annotation."""
    cls_id = int(box.cls)
    x, y, w, h = box.xywh[0].tolist()

    return CreateObjectDetection(
        class_name=class_names[cls_id],
        x=round(x - w / 2),
        y=round(y - h / 2),
        width=max(1, round(w)),
        height=max(1, round(h)),
        confidence=float(box.conf),
    )


def predict_using_yolo26(
    dataset: ls.ImageDataset,
    model_name: str = "yolo26n.pt",
    conf: float = 0.25,
    annotation_source: str | None = None,
) -> int:
    model = YOLO(model_name)
    if annotation_source is None:
        annotation_source = f"{model_name}_prediction"
    total_annotations = 0

    for sample in dataset:
        result = model.predict(source=sample.file_path_abs, conf=conf, verbose=False)[0]
        annotations = [
            yolo_box_to_annotation(box, result.names)
            for box in (result.boxes or [])
        ]
        if annotations:
            sample.add_annotations(
                annotations=annotations,
                annotation_source=annotation_source,
            )
            total_annotations += len(annotations)
    return total_annotations
```

`predict_using_yolo26` loads the checkpoint (downloading `yolo26n.pt` on first use), runs inference on every sample above the confidence threshold, and writes the resulting boxes to the dataset under a named annotation source. Predictions are kept separate from `ground_truth` so the evaluation step can compare the two layers side by side.

Run predictions on the dataset you loaded above:

```python
PRED_ANNOTATION_SOURCE = "yolo26n.pt_prediction"

predict_using_yolo26(dataset, annotation_source=PRED_ANNOTATION_SOURCE)
```

!!! warning
    Pass an explicit `annotation_source` when re-running with different settings. Otherwise, the new predictions are appended to the existing layer instead of replacing it.

**Expected result:** predictions appear in Studio under the annotation source `yolo26n.pt_prediction`.

!!! todo "Media placeholder"
    Add a GIF opening the GUI and showing the predictions are available.

### Option B: YOLO plugin in Studio

Install the plugin once per environment:

```bash
pip install "git+https://github.com/lightly-ai/lightly-studio-plugins.git#subdirectory=plugins/yolo_object_detection/"
```

The plugin is auto-discovered the next time Studio starts.

1. Open the menu on the top right and click **Plugins**.
2. Click **YOLO Object Detection**.
3. Set **model_path** to `yolo26n.pt`.
4. Set **confidence** to `0.25`.
5. Click **Execute** to run it on all images, or on the current filtered view.

Predictions are stored under the annotation source `yolo_auto_label__yolo26n.pt`, or a custom name if you set **annotation_source**. If you use the plugin instead of Python, use that name as `pred_annotation_source` in the next section.

!!! todo "Media placeholder"
    Add a GIF of the operator panel running YOLO26 with predictions appearing on the images.

## Run evaluation

### In Python

Create an evaluation run that compares your predictions against the ground truth:

```python
from lightly_studio.evaluation.image_dataset_evaluate import ObjectDetectionEvaluationConfig

dataset.evaluate().object_detection(
    name="gt_yolo26n",
    gt_annotation_source="ground_truth",
    pred_annotation_source=PRED_ANNOTATION_SOURCE,  # match your prediction source name
    config=ObjectDetectionEvaluationConfig(
        iou_threshold=0.5,
        classwise=True,
    ),
)

ls.start_gui()
```

| Config | When to use |
| --- | --- |
| `classwise=True` | Standard per-class matching (default) |
| `classwise=False` | Also count class-confusion pairs |
| `iou_threshold` | `0.5` for typical object detection |

Only images that have both ground truth and predictions are evaluated. See [Model Evaluation](../concepts_and_tools/evaluation.md) for how matching and metrics are computed.

!!! tip "Checkpoint"
    At this point your script covers the full workflow: load images and labels, run YOLO26 predictions, evaluate against ground truth, and open Studio to explore the results.

### In the Studio GUI

You can also create an evaluation run directly in the GUI, without the Python snippet above:

1. Open the **Evaluation** panel.
2. Click **Create run** and pick the ground-truth source, prediction source, and IoU threshold.
3. Name the run, for example `gt_yolo26n`, and start it.

!!! todo "Media placeholder"
    Add a GIF creating an evaluation run and the summary appearing.

## Read the metrics

Each evaluated image gets three per-sample metrics:

| Metric | Meaning |
| --- | --- |
| `tp` | True positives — correct detections |
| `fp` | False positives — the model predicted something that isn't there, or matched incorrectly |
| `fn` | False negatives — missed ground-truth objects |

!!! todo "Media placeholder"
    Add a GIF opening an image and interacting with the evaluation matches view.

### Confusion matrix

Open the confusion matrix for your evaluation run in the **Evaluation** panel.

- Rows are the ground-truth class; the last row, `(no ground truth)`, holds pure false positives.
- Columns are the predicted class; the last column, `(no prediction)`, holds pure false negatives.
- Hot cells off the diagonal point to systematic class confusion, for example `dog` predicted as `cat`.
- A high `(no prediction)` column for a class means the model misses that class.
- A high `(no ground truth)` row means the model hallucinates that class, or its localization is off.

See [Model Evaluation](../concepts_and_tools/evaluation.md#model-evaluation-in-the-gui) for more on reading the confusion matrix.

!!! todo "Media placeholder"
    Add a GIF clicking a confusion matrix cell and showing the filtered image list.

### Sort and filter by failures

In the image grid, sort by `fp` or `fn` for your evaluation run, descending, to surface the worst images first.

!!! todo "Media placeholder"
    Add a GIF sorting by `fp` in descending order.

In the embedding plot, you can then group failures by visual similarity:

1. Select the worst images from the sorted grid and tag them, for example `fp_yolo26n`.
2. Open the embedding plot and color points by tag.
3. Look for clusters — groups of visually similar images that share the same failure mode, such as small objects, night scenes, or class confusion.

!!! todo "Media placeholder"
    Add a GIF sorting by `fp`, tagging the worst samples, then coloring the embedding plot by tag and zooming into a cluster.

### Tag failures from Python

You can also tag samples with high false positives or false negatives from a script:

```python
from lightly_studio.core.dataset_query import EvaluationMetricField, SampleEvaluationQuery

dataset.query().match(
    SampleEvaluationQuery("gt_yolo26n", EvaluationMetricField("fp") > 0)
).add_tag("fp_gt_yolo26n")

dataset.query().match(
    SampleEvaluationQuery("gt_yolo26n", EvaluationMetricField("fn") > 0)
).add_tag("fn_gt_yolo26n")
```

### Compare checkpoints

To compare two models, run predictions and evaluation for each, then compare the confusion matrices and per-class `fp`/`fn` in Studio:

```python
predict_using_yolo26(dataset, model_name="yolo26n.pt", annotation_source="yolo26n.pt_prediction")
predict_using_yolo26(dataset, model_name="yolo26s.pt", annotation_source="yolo26s.pt_prediction")

dataset.evaluate().object_detection(
    name="gt_yolo26n",
    gt_annotation_source="ground_truth",
    pred_annotation_source="yolo26n.pt_prediction",
    config=ObjectDetectionEvaluationConfig(iou_threshold=0.5, classwise=True),
)
dataset.evaluate().object_detection(
    name="gt_yolo26s",
    gt_annotation_source="ground_truth",
    pred_annotation_source="yolo26s.pt_prediction",
    config=ObjectDetectionEvaluationConfig(iou_threshold=0.5, classwise=True),
)
```

## Fix issues in Studio

Failures fall into three buckets. Work through them in this order.

### Wrong ground-truth annotations

High `fp` or `fn` on an image does not always mean the model failed: mislabeled, missing, or shifted ground-truth boxes inflate both metrics. Fix labels in the `ground_truth` layer and re-run evaluation so the metrics reflect model performance, not annotation noise — retraining on bad labels will not improve results.

1. Review the high-`fp` and high-`fn` images side by side, ground truth against predictions.
2. If the label is wrong, fix the box in the `ground_truth` layer: move it, resize it, change its class, or add or remove it.
3. Otherwise, tag the sample `wrong_annotation` to fix later.

!!! todo "Media placeholder"
    Add a GIF editing a mislabeled box and adding the `wrong_annotation` tag.

### Real model failures

When the ground truth is correct, persistent `fp` and `fn` point to real gaps in the model: confused classes, hard scenes, or objects the checkpoint never learned well. Tag failures by pattern and use embedding clusters to group similar problems, so you know what to address in the next training round instead of chasing label fixes.

Tag by pattern, for example `failure_small_objects` or `failure_class_confusion_dog_cat`, then use tags together with embedding clusters to batch similar problems.

### Not enough data

A small cluster with high `fn` suggests a failure mode, but metrics on only a handful of images are not reliable — you cannot tell whether the model truly struggles on that scenario or you simply lack coverage. Add and label more images similar to that cluster, then re-run evaluation so the failure rate for that scenario becomes statistically meaningful before you prioritize retraining or vendor work.

```python
dataset.add_images_from_path(path="path/to/new/images")
```

Label the new images in Studio, then re-run predictions and evaluation.

!!! todo "Media placeholder"
    Add a GIF adding images via script, labeling them in Studio, and re-evaluating.

## Export for an annotation vendor

If you have many `wrong_annotation` images, export them for your labeling team.

1. Filter or sort to the problematic samples.
2. Select them in the grid and add the tag `wrong_annotation`.
3. Export the ground-truth annotations: open the export dialog, choose the **Image Object Detection** export type, select the `ground_truth` annotation source, and download.
4. Export the image file list: open the export dialog, choose the **Image Filenames** export type, select the `wrong_annotation` tag, and download.

Ship the exported JSON and image paths (or copied images) to the vendor, with instructions to correct the `ground_truth` boxes.

!!! todo "Media placeholder"
    Add a GIF tagging a bulk selection, exporting, and showing the output JSON.

## Conclusion

In this tutorial, we evaluated a YOLO26 model against ground-truth labels in LightlyStudio, using an example COCO dataset.

We loaded images and ground-truth annotations, ran YOLO26 predictions with both the Python API and the Studio plugin, and created an evaluation run to compare the two annotation layers. We then used per-sample metrics, the confusion matrix, and the embedding plot to separate wrong ground-truth annotations from real model failures and data gaps.

Finally, we tagged the samples that need attention and exported them for an annotation vendor to fix.

This workflow provides a practical way to go from a trained model and a labeled dataset to a prioritized list of concrete next steps: label fixes, targeted retraining, or additional data collection.
