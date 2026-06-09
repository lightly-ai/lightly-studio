# Annotations

Annotations in LightlyStudio allow you to view, create, edit, and delete annotations on your
samples in the GUI or via the [Python API](../api/annotation.md). Supported annotation types
include object detection, segmentation, and classification. You can import annotations from common
formats like COCO or YOLO and more. See [Image Dataset](../dataset_setup/image_dataset.md) and
[Video Dataset](../dataset_setup/video_dataset.md) for the available import workflows and supported
formats.

!!! info "Terminology"
    - **Annotation** — a classification, object-detection box, or segmentation mask attached to a sample.
    - **Annotation class** — the category of an annotation, e.g. `"dog"` or `"cat"`.
    - **Annotation source** — a named group of annotations from one origin, e.g. ground truth, a model's predictions, or an annotator.

## Annotations in the GUI

Annotations are shown in sample detail view and in dedicated annotation-focused views in the app. Use `Edit Annotations` to create, update, or delete annotations directly in the GUI.

<div style="width: 100%; aspect-ratio: 16 / 9; overflow: hidden;">
  <iframe
    style="width: 100%; height: 100%; border: 0;"
    src="https://www.youtube.com/embed/IZTkloqpZ4k?autoplay=1&mute=1&playsinline=1&rel=0"
    title="LightlyStudio annotations workflow"
    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
    referrerpolicy="strict-origin-when-cross-origin"
    allowfullscreen
  ></iframe>
</div>

## Annotations in Python

Use the Python API when you want to inspect annotations programmatically, generate them from model
predictions, or import custom annotation outputs. Predictions and human annotations are treated as the same concept in LightlyStudio. Any functions for annotations can also process predictions. Predictions can additionally have an optional `confidence` value. See
[Annotation API Reference](../api/annotation.md) for the full API surface.

### Annotation sources

Every annotation belongs to an annotation source. Annotation sources group related annotations, for
example ground truth, predictions from one model run, or annotations from different annotators.

This lets you keep multiple annotation sources for the same samples separate. In the GUI, you can
inspect individual annotation sources, visualize multiple sources together, and compare them via evaluation runs.

### Adding annotations

For most workflows, the easiest way to add annotations is to import them from supported formats such as COCO and YOLO, either while adding samples to the dataset or later by attaching annotations to already indexed samples:

```python
# Add images and annotations together.
dataset.add_samples_from_coco(
    annotations_json="/path/to/instances.json",
    images_path="/path/to/images",
)

# Add annotations to images that are already indexed.
# Prediction confidence is loaded from the JSON `score` field.
dataset.add_annotations_from_coco(
    annotations_json="/path/to/predictions.json",
    images_root="/path/to/images",
    annotation_source="predictions",
)
```

When images are already in the dataset, the dataset-level `add_annotations_from_*` helpers import
annotations into a named annotation source. This named-source workflow is currently supported for image
datasets via
[`add_annotations_from_coco`](../api/dataset.md#lightly_studio.ImageDataset),
[`add_annotations_from_yolo`](../api/dataset.md#lightly_studio.ImageDataset), and
[`add_annotations_from_labelformat`](../api/dataset.md#lightly_studio.ImageDataset).
All of these helpers take an `annotation_source` argument, which becomes the annotation source name.

Reusing the same `annotation_source` appends annotations to the existing annotation source. Using a new `annotation_source` creates a new
annotation source.

```python
import lightly_studio as ls

dataset = ls.ImageDataset.create()
dataset.add_images_from_path(path="./path/to/images")

dataset.add_annotations_from_coco(
    annotations_json="./ground_truth.json",
    images_root="./path/to/images",
    annotation_source="ground_truth",
)

dataset.add_annotations_from_coco(
    annotations_json="./predictions_model_a.json",
    images_root="./path/to/images",
    annotation_source="model_a",
)

dataset.add_annotations_from_yolo(
    data_yaml="./yolo_dataset/data.yaml",
    annotation_source="annotator_b",
)
```

This is the recommended way to keep multiple annotation sources separate in the same dataset. If
your predictions are already stored in COCO format, `add_annotations_from_coco(...)` also supports
loading them. For prediction files, LightlyStudio looks for a `score` field in each COCO
annotation object and stores it as annotation confidence.

See [ImageDataset](../api/dataset.md#imagedataset) and
[VideoDataset](../api/dataset.md#videodataset) for the full import workflows and supported
formats. Predictions can be added the same way as other annotations, including optional confidence
scores. If you need to create annotations directly from Python, add them to samples with
[`add_annotation`](../api/sample.md#lightly_studio.core.sample.Sample.add_annotation). The
following example creates an object detection annotation:

```python
from lightly_studio.core.annotation import CreateObjectDetection

sample.add_annotation(
    CreateObjectDetection(
        class_name="car",
        confidence=0.9,  # optional
        x=10,
        y=20,
        width=30,
        height=40,
    )
)
```

There are also [CreateClassification](../api/annotation.md#createclassification) and
[CreateSegmentationMask](../api/annotation.md#createsegmentationmask) classes for the other
annotation types.

For segmentation annotations, prefer
[`from_binary_mask`](../api/annotation.md#lightly_studio.core.annotation.CreateSegmentationMask.from_binary_mask),
which automatically derives the bounding box and mask encoding from a 2D numpy array:

```python
import numpy as np
from lightly_studio.core.annotation import CreateSegmentationMask

mask = np.array([
    [0, 0, 0, 0],
    [0, 1, 1, 0],
    [0, 1, 1, 0],
    [0, 0, 0, 0],
])

sample.add_annotation(
    CreateSegmentationMask.from_binary_mask(
        class_name="car",
        binary_mask=mask,
        confidence=0.85,  # optional
    )
)
```

If you already have masks in RLE form, use
[`from_rle_mask`](../api/annotation.md#lightly_studio.core.annotation.CreateSegmentationMask.from_rle_mask).

??? note "RLE mask format details"

    For segmentation annotations
    ([`CreateSegmentationMask`](../api/annotation.md#createsegmentationmask)), `segmentation_mask`
    is expected to be a list of integers representing the binary mask in a row-wise
    Run-Length Encoding (RLE) format.

    The format follows these rules:

    - The encoding is flattened row by row.
    - The first number represents the count of 0s (background) at the start.
    - If the mask starts with a 1 (foreground), the first number must be 0.
    - Subsequent numbers represent alternating counts of 1s and 0s.

    Example 2x4 mask:
    ```
    [[0, 1, 1, 0],
     [1, 1, 1, 1]]
    ```

    Flattened row-wise, this becomes:
    ```
    [0, 1, 1, 0, 1, 1, 1, 1]
    ```

    The resulting `segmentation_mask` is:
    ```
    [1, 2, 1, 4]
    ```

### Accessing annotations

You can access annotations of each sample after creating them in the GUI, importing them from a
dataset format such as COCO or YOLO, or adding them programmatically from Python.

```python
from lightly_studio.core.annotation import ObjectDetectionAnnotation

for sample in dataset:
    for annotation in sample.annotations:
        if isinstance(annotation, ObjectDetectionAnnotation):
            print(annotation.x, annotation.y, annotation.width, annotation.height)
```

There are 3 annotation types:
[ClassificationAnnotation](../api/annotation.md#classificationannotation),
[SegmentationMaskAnnotation](../api/annotation.md#segmentationmaskannotation), and
[ObjectDetectionAnnotation](../api/annotation.md#objectdetectionannotation).

See [Annotation](../api/annotation.md) for the full annotation API reference and [Search and Filter](search_and_filter.md) for annotation-based querying. For end-to-end dataset setup examples, see [Image Dataset](../dataset_setup/image_dataset.md) and [Video Dataset](../dataset_setup/video_dataset.md).
