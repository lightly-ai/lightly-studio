# Annotations

Annotations in LightlyStudio let you view, create, edit, delete, import, and compare labels on
your samples. Supported annotation types include object detection, segmentation, and
classification. You can work with annotations in the GUI or through the
[Python API](../api/annotation.md).

## Annotation Collections

Every annotation belongs to an annotation collection. Annotation collections group related
annotations, for example ground truth, predictions from one model run, or annotations from
different annotators.

This lets you keep multiple annotation sources for the same samples separate. In the GUI, you
can inspect collections individually, visualize multiple collections together, and compare
collections via evaluation runs.

## Annotations in the GUI

Annotations are shown in sample detail view and in dedicated annotation-focused views in the app.
Use `Edit Annotations` to create, update, or delete annotations directly in the GUI.

When a dataset contains multiple annotation collections, you can use the GUI to inspect each
collection independently. You can also visualize annotations from multiple collections together,
which is useful for comparing ground truth against predictions or comparing different annotators.

<div style="width: 100%; aspect-ratio: 16 / 9; overflow: hidden;">
  <iframe
    style="width: 100%; height: 100%; border: 0;"
    src="https://www.youtube.com/embed/IZTkloqpZ4k"
    title="LightlyStudio annotations workflow"
    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
    referrerpolicy="strict-origin-when-cross-origin"
    allowfullscreen
  ></iframe>
</div>

## Annotations in Python

Use the Python API when you want to inspect annotations programmatically, generate them from model
predictions, or import custom annotation outputs. See
[Annotation API Reference](../api/annotation.md) for the full annotation API surface.

### Accessing annotations

You can access annotations of each sample. They can be created in the GUI or imported, for example
from COCO format. See the [COCO Segmentation Mask](../index.md#quickstart) example for one import
workflow.

```py
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

### Adding annotations directly

Add annotations to samples with
[`add_annotation`](../api/sample.md#lightly_studio.core.sample.Sample.add_annotation). The
following example creates an object detection annotation:

```python
from lightly_studio.core.annotation import CreateObjectDetection

sample.add_annotation(
    CreateObjectDetection(
        label="car",
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

Direct calls to `sample.add_annotation(...)` are useful for creating annotations from Python, but
they do not let you choose a custom annotation collection name. If you want to group imported
annotations into a specific collection such as `ground_truth`, `annotator_a`, or `model_v1`, use
one of the dataset-level `add_annotations_from_*` helper methods described below.

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
        label="car",
        binary_mask=mask,
        confidence=0.85,  # optional
    )
)
```

Alternatively, provide the mask encoding directly with
[`from_rle_mask`](../api/annotation.md#lightly_studio.core.annotation.CreateSegmentationMask.from_rle_mask):

```python
from lightly_studio.core.annotation import CreateSegmentationMask

# E.g., for a 2x4 mask:
# [[0, 1, 1, 0],
#  [1, 1, 1, 1]]
# A row-wise Run-Length Encoding (RLE) mask is: [1, 2, 1, 4]
sample.add_annotation(
    CreateSegmentationMask.from_rle_mask(
        label="car",
        segmentation_mask=[1, 2, 1, 4],
        # `sample` could be ImageSample or another 2D sample, such as a video frame
        sample_2d=sample,
        confidence=0.85,  # optional
    )
)
```

??? note "Binary Mask Format"

    For segmentation annotations
    ([`CreateSegmentationMask`](../api/annotation.md#createsegmentationmask)), `segmentation_mask`
    is expected to be a list of integers representing the binary mask in a row-wise
    Run-Length Encoding (RLE) format.

    !!! tip
        We recommend using
        [`from_binary_mask`](../api/annotation.md#lightly_studio.core.annotation.CreateSegmentationMask.from_binary_mask)
        to generate this encoding automatically from a numpy array.

    The format follows these rules:

    - The encoding is flattened row by row.
    - The first number represents the count of 0s (background) at the start.
    - If the mask starts with a 1 (foreground), the first number must be 0.
    - Subsequent numbers represent alternating counts of 1s and 0s.

    For example, consider a 2x4 mask:
    ```
    [[0, 1, 1, 0],
     [1, 1, 1, 1]]
    ```
    Flattened row-wise: `[0, 1, 1, 0, 1, 1, 1, 1]`.

    There are 4 sequences of identical bits: one 0, two 1s, one 0, and four 1s. The resulting `segmentation_mask` is `[1, 2, 1, 4]`.

### Adding annotations to a named collection

When you are working with images and they are already in the dataset, use the dataset-level helper
methods to import annotations into a specific annotation collection. This named-collection import
workflow is currently supported for image datasets. All of these helpers take a `name` argument,
which becomes the annotation collection name:

- [`ImageDataset.add_annotations_from_coco`](../api/dataset.md#imagedataset)
- [`ImageDataset.add_annotations_from_yolo`](../api/dataset.md#imagedataset)
- [`ImageDataset.add_annotations_from_labelformat`](../api/dataset.md#imagedataset)

Reusing the same `name` appends annotations to the existing collection. Using a new `name` creates
a new annotation collection.

```python
import lightly_studio as ls

dataset = ls.ImageDataset.create()
dataset.add_images_from_path(path="./path/to/images")

dataset.add_annotations_from_coco(
    annotations_json="./ground_truth.json",
    images_root="./path/to/images",
    name="ground_truth",
)

dataset.add_annotations_from_coco(
    annotations_json="./predictions_model_a.json",
    images_root="./path/to/images",
    name="model_a",
)

dataset.add_annotations_from_yolo(
    data_yaml="./yolo_dataset/data.yaml",
    name="annotator_b",
)
```

This is the recommended way to keep multiple annotation sources separate in the same dataset.

### Indexing predictions

Prediction annotations are regular annotations with an optional confidence score. For object
detection predictions, set `confidence` when creating the annotation manually:

```py
import lightly_studio as ls
from lightly_studio.core.annotation import CreateObjectDetection

dataset = ls.ImageDataset.create()
dataset.add_images_from_path(path="./path/to/image_folder")

predictions = {
    "img1.jpg": {"x": 100, "y": 150, "w": 200, "h": 300, "conf": 0.95},
    "img2.jpg": {"x": 50, "y": 80, "w": 120, "h": 250, "conf": 0.87},
}

for image_sample in dataset:
    pred = predictions[image_sample.file_name]
    image_sample.add_annotation(
        CreateObjectDetection(
            label="person",
            confidence=pred["conf"],  # optional, must be between 0.0 and 1.0
            x=pred["x"],
            y=pred["y"],
            width=pred["w"],
            height=pred["h"],
        )
    )
```

If your predictions are already stored in COCO format, `add_annotations_from_coco(...)` also
supports loading them. For prediction files, LightlyStudio looks for a `score` field in each COCO
annotation object and stores it as annotation confidence.

!!! note "Embeddings not supported"
    Manual annotation indexing does not generate embeddings. Features like similarity search and
    embedding plots are not available for manually indexed samples.

See [Annotation](../api/annotation.md) for the full annotation API reference,
[Dataset](../api/dataset.md) for the dataset import helpers, and
[Search and Filter](search_and_filter.md) for annotation-based querying.
