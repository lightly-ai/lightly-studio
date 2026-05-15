# Python API

LightlyStudio has a powerful Python interface. You can not only index datasets but also query and manipulate them using code.

## Overview

- **Dataset setup** — [Image Dataset](../dataset_setup/image_dataset.md), [Video Dataset](../dataset_setup/video_dataset.md)
- **Reuse Datasets** — [Reuse Datasets](../advanced/reuse_datasets.md) covers the DuckDB file location and `load_or_create` workflow.
- **Cloud Storage** — [Cloud Storage](../advanced/cloud_storage.md) covers loading images and videos directly from S3, GCS, and Azure.
- **Search and Filter** — [Search and Filter](../concepts_and_tools/search_and_filter.md) covers the `DatasetQuery` API for filtering, sorting, and slicing.
- **Sampling** — [Sampling](../concepts_and_tools/sampling.md) covers diverse, metadata-weighted, similarity, class-balancing, and combined sampling strategies.

The full API reference for each module is available in the navigation sidebar:
[Dataset](dataset.md), [Sample](sample.md), [DatasetQuery](dataset_query.md), [Selection](selection.md), [Plugin](plugin.md), [Annotation](annotation.md).

## Annotations

You can access annotations of each sample. They can be created in the GUI or imported, e.g. from the COCO format, see the [COCO Segmentation Mask](../index.md#quickstart) example. The [Indexing with Predictions](#indexing-with-predictions) section below shows how to create annotations from Python.

### Accessing annotations

```py
from lightly_studio.core.annotation import ObjectDetectionAnnotation

for sample in dataset:
    for annotation in sample.annotations:
        if isinstance(annotation, ObjectDetectionAnnotation):
            print(annotation.x, annotation.y, annotation.width, annotation.height)
```

There are 3 different types: `ClassificationAnnotation`, `SegmentationMaskAnnotation`, and `ObjectDetectionAnnotation`.

### Adding annotations

You can add annotations to samples using the `add_annotation` method, the following example shows how to create an object detection annotation.

```python
from lightly_studio.core.annotation import CreateObjectDetection

# Add an object detection annotation to a sample
sample.add_annotation(CreateObjectDetection(
    label="car",
    confidence=0.9,  # optional
    x=10,
    y=20,
    width=30,
    height=40,
))
```

There are also `CreateClassification` and `CreateSegmentationMask` classes for other annotation types.

For segmentation annotations, it is recommended to use the `from_binary_mask` method, which automatically handles the bounding box and mask encoding from a 2D numpy array:

```python
import numpy as np
from lightly_studio.core.annotation import CreateSegmentationMask

# A 2D numpy array representing the binary mask (1 for foreground, 0 for background)
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
        confidence=0.85, # optional
    )
)
```

Alternatively, you can provide the mask encoding using the `from_rle_mask` method:

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
        confidence=0.85, # optional
    )
)
```


??? note "Binary Mask Format"

    For segmentation annotations (`CreateSegmentationMask`), the `segmentation_mask` is expected to be a list of integers representing the binary mask in a row-wise Run-Length Encoding (RLE) format.

    !!! tip
        We recommend using the `from_binary_mask` method described above to automatically generate this encoding from a numpy array.

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

    There are 4 sequences of identical bits: one 0, two 1s, one 0 and four 1s. The resulting `segmentation_mask` is `[1, 2, 1, 4]`.

### Indexing with Predictions

If you need to index model predictions with confidence scores or work with custom annotation formats, you can leverage the annotation API.

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
            confidence=pred["conf"],  # Optional model confidence, must be between 0.0 and 1.0
            x=pred["x"],
            y=pred["y"],
            width=pred["w"],
            height=pred["h"],
        )
    )
```

!!! note "Embeddings not supported"
    Manual indexing does not generate embeddings. Features like similarity search and embedding plots will not be available for manually indexed samples.

## API Reference

See the menu on the left for the full API reference of the Python interface.
