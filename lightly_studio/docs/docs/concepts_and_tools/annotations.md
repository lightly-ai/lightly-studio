# Annotations

Annotations in LightlyStudio allow you to view, create, edit, and delete annotation labels on your samples in the GUI via the Python API. Supported annotation types include object detections, segmentations and classifications. You can import annotations from common formats like COCO or YOLO and more.

## Annotations in the GUI

Annotations are shown in sample detail view and in dedicated annotation-focused views in the app. Use `Edit Annotations` to create, update, or delete annotations directly in the GUI.

<div style="text-align: center;">
  <iframe
    width="560"
    height="315"
    src="https://www.youtube.com/embed/IZTkloqpZ4k"
    title="LightlyStudio annotations workflow"
    frameborder="0"
    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
    referrerpolicy="strict-origin-when-cross-origin"
    allowfullscreen
  ></iframe>
</div>

You can add annotations during dataset setup through supported import workflows, through the [Python API](#adding-annotations), or manually in the GUI. For example, image datasets can load annotations from formats such as COCO, YOLO, and Pascal VOC, and video datasets support YouTube-VIS imports. See [Image Dataset](../dataset_setup/image_dataset.md) and [Video Dataset](../dataset_setup/video_dataset.md) for the available import workflows and supported formats.

## Annotations in Python

Use the Python API when you want to inspect annotations programmatically, generate them from model predictions, or import custom annotation outputs.

## Accessing annotations

You can access annotations of each sample. They can be created in the GUI or imported, for example from COCO format. See the [COCO Segmentation Mask](../index.md#quickstart) example for one import workflow.

```py
from lightly_studio.core.annotation import ObjectDetectionAnnotation

for sample in dataset:
    for annotation in sample.annotations:
        if isinstance(annotation, ObjectDetectionAnnotation):
            print(annotation.x, annotation.y, annotation.width, annotation.height)
```

There are 3 annotation types: `ClassificationAnnotation`, `SegmentationMaskAnnotation`, and
`ObjectDetectionAnnotation`.

## Adding annotations

Add annotations to samples with `add_annotation`. The following example creates an object detection annotation:

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

There are also `CreateClassification` and `CreateSegmentationMask` classes for the other annotation types.

For segmentation annotations, prefer `from_binary_mask`, which automatically derives the bounding box and mask encoding from a 2D numpy array:

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

Alternatively, provide the mask encoding directly with `from_rle_mask`:

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

    For segmentation annotations (`CreateSegmentationMask`), `segmentation_mask` is expected to be a list of integers representing the binary mask in a row-wise Run-Length Encoding (RLE) format.

    !!! tip
        We recommend using `from_binary_mask` to generate this encoding automatically from a numpy
        array.

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

## Indexing with predictions

If you need to index model predictions with confidence scores or work with custom annotation formats, you can create annotations directly from Python.

```py
import lightly_studio as ls
from lightly_studio.core.annotation import CreateObjectDetection

dataset = ls.ImageDataset.create()
dataset.add_images_from_path(path="./path/to/image_folder")

# Your model predictions (e.g., from a detector)
predictions = {
    "img1.jpg": {"x": 100, "y": 150, "w": 200, "h": 300, "conf": 0.95},
    "img2.jpg": {"x": 50, "y": 80, "w": 120, "h": 250, "conf": 0.87},
}

for image_sample in dataset:
    pred = predictions[image_sample.file_name]
    image_sample.add_annotation(
        CreateObjectDetection(
            label="person",
            confidence=pred["conf"],  # Optional, must be between 0.0 and 1.0
            x=pred["x"],
            y=pred["y"],
            width=pred["w"],
            height=pred["h"],
        )
    )
```

!!! note "Embeddings not supported"
    Manual indexing does not generate embeddings. Features like similarity search and embedding plots are not available for manually indexed samples.

See [Annotation](../api/annotation.md) for the full annotation API reference and [Search and Filter](search_and_filter.md) for annotation-based querying.
