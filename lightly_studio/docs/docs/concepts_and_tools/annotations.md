# Annotations

LightlyStudio supports three annotation types:

- classification,
- object detection, and
- segmentation.

You can inspect and edit annotations in the GUI, or add and read them in Python. For dataset-level
imports such as COCO, YOLO, and Label Studio format, see [Image Dataset](../dataset_setup/image_dataset.md)
and [Video Dataset](../dataset_setup/video_dataset.md).

!!! info "Terminology"
    - **Annotation**: A classification, object-detection box, or segmentation mask attached to a sample.
    - **Prediction**: An annotation with an optional confidence score.
    - **Annotation class**: The category of an annotation, e.g. `"dog"` or `"cat"`.
    - **Annotation source**: A named group of annotations, e.g. `ground_truth` or `model_a`.
    

## Annotations in the GUI

Annotations are shown in sample detail view and in the annotation-focused views. Use
`Edit Annotations` to create, update, or delete them.

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

## Object-level embeddings

LightlyStudio computes embeddings not only for whole images, but also for individual
objects defined by object-detection boxes or segmentation masks. This unlocks the
**embedding plot** and **similarity search** on individual objects, working exactly the
same way they do for whole images.
Open the `Annotations` view in the GUI to browse objects in a grid, search them, and
explore them in the embedding plot. For how search, filter, and the embedding plot
behave, see [Search and Filter](search_and_filter.md).


Object embeddings are created automatically when object detection or segmentation annotations are imported. The
`add_annotations_from_*` methods accept `embed_annotations=True` by default. Pass
`embed_annotations=False` to skip it.

!!! warning "Editing an annotation does not update its embedding"
    Object-level embeddings are generated only for annotations that do not yet have one. Editing an
    existing annotation — for example moving or resizing its bounding box — does **not** regenerate
    its embedding, so the object keeps the embedding of its original crop. We plan to add support
    for recomputing object embeddings after edits.

## Annotations in Python

Use the [Python API](../api/annotation.md) to create annotations and predictions directly, import them from model
outputs, or inspect them programmatically.

### Classification

Use [CreateClassification](../api/annotation.md#createclassification) for sample-level labels:

```python
from lightly_studio.core.annotation import CreateClassification

sample.add_annotation(
    CreateClassification(
        class_name="cat",
        confidence=0.95,  # optional
    )
)
```

### Object Detection

Use [CreateObjectDetection](../api/annotation.md#createobjectdetection) for bounding boxes:

```python
from lightly_studio.core.annotation import CreateObjectDetection

sample.add_annotation(
    CreateObjectDetection(
        class_name="car",
        x=10,
        y=20,
        width=30,
        height=40,
        confidence=0.9,  # optional
    )
)
```

To import object detection annotations at the dataset level, use
[add_annotations_from_coco](../api/dataset.md#lightly_studio.ImageDataset.add_annotations_from_coco),
[add_annotations_from_yolo](../api/dataset.md#lightly_studio.ImageDataset.add_annotations_from_yolo),
or
[add_annotations_from_labelformat](../api/dataset.md#lightly_studio.ImageDataset.add_annotations_from_labelformat).

### Segmentation

Use [CreateSegmentationMask](../api/annotation.md#createsegmentationmask) for segmentation masks.
In most cases, [`from_binary_mask(...)`](../api/annotation.md#lightly_studio.core.annotation.CreateSegmentationMask.from_binary_mask) is the easiest option:

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

If you already have RLE masks, use
[from_rle_mask](../api/annotation.md#lightly_studio.core.annotation.CreateSegmentationMask.from_rle_mask).

??? note "RLE mask format details"

    For segmentation annotations,
    [`CreateSegmentationMask`](../api/annotation.md#createsegmentationmask) expects
    `segmentation_mask` as row-wise Run-Length Encoding (RLE):

    - Flatten the mask row by row.
    - The first number counts leading background pixels.
    - If the mask starts with foreground, the first number must be `0`.
    - Counts then alternate between foreground and background.

    Example 2x4 mask:
    ```
    [[0, 1, 1, 0],
     [1, 1, 1, 1]]
    ```

    Flattened:
    ```
    [0, 1, 1, 0, 1, 1, 1, 1]
    ```

    Encoded:
    ```
    [1, 2, 1, 4]
    ```

To import segmentation annotations at the dataset level, use
[add_annotations_from_coco](../api/dataset.md#lightly_studio.ImageDataset.add_annotations_from_coco),
[add_annotations_from_labelformat](../api/dataset.md#lightly_studio.ImageDataset.add_annotations_from_labelformat),
or
[add_annotations_from_pascal_voc_segmentations](../api/dataset.md#lightly_studio.ImageDataset.add_annotations_from_pascal_voc_segmentations).


### Predictions

Predictions are represented by the same objects as annotations. The only difference is that
predictions can include a `confidence` value and are usually stored in their own annotation source.

For image datasets, the `add_annotations_from_*` methods are the easiest way to import 
predictions into a named source:

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
```

Supported methods:

- [add_annotations_from_coco](../api/dataset.md#lightly_studio.ImageDataset.add_annotations_from_coco)
- [add_annotations_from_yolo](../api/dataset.md#lightly_studio.ImageDataset.add_annotations_from_yolo)
- [add_annotations_from_labelformat](../api/dataset.md#lightly_studio.ImageDataset.add_annotations_from_labelformat)
- [add_annotations_from_pascal_voc_segmentations](../api/dataset.md#lightly_studio.ImageDataset.add_annotations_from_pascal_voc_segmentations)
 
If the input is a COCO prediction file, LightlyStudio reads the `score` field and stores it as
annotation confidence.

### Reading annotations

Each sample exposes its annotations through `sample.annotations`:

```python
from lightly_studio.core.annotation import ObjectDetectionAnnotation

for sample in dataset:
    for annotation in sample.annotations:
        if isinstance(annotation, ObjectDetectionAnnotation):
            print(annotation.x, annotation.y, annotation.width, annotation.height)
```

Available annotation classes:

- [ClassificationAnnotation](../api/annotation.md#classificationannotation)
- [ObjectDetectionAnnotation](../api/annotation.md#objectdetectionannotation)
- [SegmentationMaskAnnotation](../api/annotation.md#segmentationmaskannotation)

See [Annotation API Reference](../api/annotation.md) for the full API and
[Search and Filter](search_and_filter.md) for annotation-based queries.
