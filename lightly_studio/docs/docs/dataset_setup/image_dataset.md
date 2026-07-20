---
title: "Image Dataset: Load and Query in Python"
description: Learn how to load images into LightlyStudio from a folder, cloud storage, or existing dataset, then explore and query them in the GUI and Python API.
---

# Image Dataset

This guide explains how to load images into LightlyStudio, how to explore them
in the GUI, and how to use the Python API to query and manipulate them.

## Load an Image Dataset

### From a Folder

Use `add_images_from_path` to load images from a folder:

```python title="Load an Image Dataset from a Folder"
import lightly_studio as ls

# We download an example dataset for this guide.
download_path = ls.utils.download_example_dataset(download_dir="dataset_examples")

# Create an empty dataset and add images from a folder.
dataset = ls.ImageDataset.create()
dataset.add_images_from_path(path=f"{download_path}/coco_subset_128_images/images")
```

The `ls.ImageDataset.create()` method call is lightweight and initializes an empty dataset.

The `add_images_from_path(...)` method accepts a path to a file or a folder. If the path is a folder,
it will recursively search for images in it. A remote path like `s3://my-bucket/my-folder` is also
supported, see [Using Cloud Storage](cloud_storage.md) for more details.

Added images are automatically embedded so that embedding plot and image search are enabled.
To skip embedding, pass `embed=False` to the method.

The method supports additional arguments, e.g. you can pass `tag_depth=1` to add the image parent
folder name as a tag to each sample. See the [API reference](../api/dataset.md#lightly_studio.ImageDataset.add_images_from_path) for full details.

### From an Annotation Format

`ImageDataset` class exposes methods to load images with annotations from a number of
standard formats. See [API reference](../api/dataset.md#lightly_studio.ImageDataset) for full details.

=== "YOLO Object Detections"

    ```python
    import lightly_studio as ls

    # Download the example dataset (will be skipped if it already exists)
    dataset_path = ls.utils.download_example_dataset(download_dir="dataset_examples")

    dataset = ls.ImageDataset.create()
    dataset.add_samples_from_yolo(
        data_yaml=f"{dataset_path}/road_signs_yolo/data.yaml",
    )
    ```

    <details>
    <summary>The YOLO format details:</summary>

    The dataset structure is:

    ```
    road_signs_yolo/
    ├── train/
    │   ├── images/
    │   │   ├── image1.jpg
    │   │   ├── image2.jpg
    │   │   └── ...
    │   └── labels/
    │       ├── image1.txt
    │       ├── image2.txt
    │       └── ...
    ├── valid/  (optional)
    │   ├── images/
    │   │   └── ...
    │   └── labels/
    │       └── ...
    └── data.yaml
    ```

    Each label file contains YOLO format annotations (one per line):

    ```
    <class> <x_center> <y_center> <width> <height>
    ```

    Where coordinates are normalized between 0 and 1.

    </details>

=== "COCO Object Detections"

    ```python
    import lightly_studio as ls

    # Download the example dataset (will be skipped if it already exists)
    dataset_path = ls.utils.download_example_dataset(download_dir="dataset_examples")

    dataset = ls.ImageDataset.create()
    dataset.add_samples_from_coco(
        annotations_json=f"{dataset_path}/coco_subset_128_images/instances_train2017.json",
        images_path=f"{dataset_path}/coco_subset_128_images/images",
    )
    ```

    <details>
    <summary>The COCO format details:</summary>

    ```
    coco_subset_128_images/
    ├── images/
    │   ├── image1.jpg
    │   ├── image2.jpg
    │   └── ...
    └── instances_train2017.json        # Single JSON file containing all annotations
    ```

    COCO uses a single JSON file containing all annotations. The format consists of three main components:

    - Images: Defines metadata for each image in the dataset.
    - Categories: Defines the object classes.
    - Annotations: Defines object bounding boxes. Note that in the example dataset the file contains
      also segmentation mask information, however we load just the bounding boxes.

    </details>

=== "COCO Segmentation Masks"

    ```python
    import lightly_studio as ls

    # Download the example dataset (will be skipped if it already exists)
    dataset_path = ls.utils.download_example_dataset(download_dir="dataset_examples")

    dataset = ls.ImageDataset.create()
    dataset.add_samples_from_coco(
        annotations_json=f"{dataset_path}/coco_subset_128_images/instances_train2017.json",
        images_path=f"{dataset_path}/coco_subset_128_images/images",
        annotation_type=ls.AnnotationType.SEGMENTATION_MASK,
    )
    ```

    <details>
    <summary>The COCO format details:</summary>

    ```
    coco_subset_128_images/
    ├── images/
    │   ├── image1.jpg
    │   ├── image2.jpg
    │   └── ...
    └── instances_train2017.json        # Single JSON file containing all annotations
    ```

    COCO uses a single JSON file containing all annotations. The format consists of three main components:

    - Images: Defines metadata for each image in the dataset.
    - Categories: Defines the object classes.
    - Annotations: Defines object instances.

    </details>

=== "COCO Captions"

    ```python
    import lightly_studio as ls

    # Download the example dataset (will be skipped if it already exists)
    dataset_path = ls.utils.download_example_dataset(download_dir="dataset_examples")

    dataset = ls.ImageDataset.create()
    dataset.add_samples_from_coco_caption(
        annotations_json=f"{dataset_path}/coco_subset_128_images/captions_train2017.json",
        images_path=f"{dataset_path}/coco_subset_128_images/images",
    )
    ```

    <details>
    <summary>The COCO format details:</summary>

    ```
    coco_subset_128_images/
    ├── images/
    │   ├── image1.jpg
    │   ├── image2.jpg
    │   └── ...
    └── captions_train2017.json        # Single JSON file containing all captions
    ```

    COCO uses a single JSON file containing all captions. The format consists of two main components:

    - Images: Defines metadata for each image in the dataset.
    - Annotations: Defines the captions.

    </details>

=== "Pascal VOC Segmentations"

    ```python
    import json
    from pathlib import Path

    import lightly_studio as ls

    # Download the example dataset (will be skipped if it already exists)
    dataset_path = ls.utils.download_example_dataset(download_dir="dataset_examples")

    # Load a mapping from class IDs to class names. The mapping is not a part of the Pascal VOC format.
    class_id_to_name_path = f"{dataset_path}/voc2012_10_images/class_id_to_name.json"
    json_dict = json.loads(Path(class_id_to_name_path).read_text())
    class_id_to_name = {int(k): v for k, v in json_dict.items()}

    # Create an image dataset and add samples from Pascal VOC format.
    dataset = ls.ImageDataset.create()
    dataset.add_samples_from_pascal_voc_segmentations(
        images_path=f"{dataset_path}/voc2012_10_images/JPEGImages",
        masks_path=f"{dataset_path}/voc2012_10_images/SegmentationClass",
        class_id_to_name=class_id_to_name,
    )
    ```

    To load Pascal VOC format, the mapping from class IDs to class names is not a part of the
    format and must be provided separately. In the example above, we load it from a JSON file,
    but you can also create it manually in Python.

    Imported masks are stored as `AnnotationType.SEGMENTATION_MASK`. Use segmentation mask type filters for querying and exporting these annotations.

    <details>
    <summary>The Pascal VOC format details:</summary>

    ```
    dataset/
    ├── images/
    │   ├── image1.jpg
    │   ├── image2.jpg
    │   └── ...
    └── masks/
        ├── image1.png
        ├── image2.png
        └── ...
    ```

    Each mask is a PNG image where each pixel value corresponds to a class ID.

    In the example above, we load a mapping from class IDs to class names from a JSON file
    in this format:

    ```json
    {
        "0": "background",
        "1": "aeroplane",
        "2": "bicycle",
        ...
    }
    ```

    </details>

=== "Custom Annotations"

    ```python
    import numpy as np

    import lightly_studio as ls
    from lightly_studio.core.annotation import (
        CreateClassification,
        CreateObjectDetection,
        CreateSegmentationMask,
    )
    from lightly_studio.core.dataset_query import ImageSampleField

    # Download the example dataset (will be skipped if it already exists)
    dataset_path = ls.utils.download_example_dataset(download_dir="dataset_examples")
    images_path = f"{dataset_path}/coco_subset_128_images/images"

    # Create an image dataset and add the images first.
    dataset = ls.ImageDataset.create()
    dataset.add_images_from_path(path=images_path)

    # Use a query to fetch the sample you want to annotate.
    sample = dataset.query().match(
        ImageSampleField.file_name == "000000565296.jpg",
    ).to_list()[0]

    # A binary mask is indexed as [row, column], so its shape is (height, width).
    binary_mask = np.zeros((sample.height, sample.width), dtype=np.uint8)
    binary_mask[160:300, 300:480] = 1

    # Add one set of annotations to this sample.
    sample.add_annotations(
        [
            CreateClassification(class_name="outdoor"),
            CreateObjectDetection(
                class_name="vehicle",
                x=80,
                y=120,
                width=180,
                height=120,
            ),
            CreateSegmentationMask.from_binary_mask(
                class_name="foreground",
                binary_mask=binary_mask,
            ),
        ],
        annotation_source="ground_truth",
    )

    ls.start_gui()
    ```

    Bounding boxes use pixel coordinates with `x` and `y` at the top-left corner.
    Segmentation masks can be created from a binary mask with shape `(height, width)`. Class names
    are added to the dataset automatically the first time they are used. The `annotation_source`
    groups annotations, for example as `ground_truth` or model outputs. To annotate multiple
    samples, iterate over a query and call `sample.add_annotations(...)` for each sample.

=== "Lightly Object Detections"

    ```python
    import lightly_studio as ls

    # Download the example dataset (will be skipped if it already exists)
    dataset_path = ls.utils.download_example_dataset(download_dir="dataset_examples")

    dataset = ls.ImageDataset.create()
    dataset.add_samples_from_lightly(
        input_folder=f"{dataset_path}/coco_subset_128_images/predictions",
    )
    ```

    Images are by default expected to be in the `../images` folder, you can specify
    `images_rel_path` to change it if needed.

    <details>
    <summary>The Lightly format details:</summary>

    ```
    dataset/
    ├── images/
    │   ├── image1.jpg
    │   └── image2.jpg
    └── predictions/
        ├── schema.json
        ├── image1.json
        └── image2.json
    ```

    The prediction folder contains a `schema.json` file defining the task type and
    categories, and one JSON file per image with the predictions.

    The `schema.json` file defines the task type and the list of categories:

    ```json
    {
        "task_type": "object-detection",
        "categories": [
            {"id": 0, "name": "person"},
            {"id": 1, "name": "bicycle"},
            {"id": 2, "name": "car"},
            ...
        ]
    }
    ```

    Each per-image JSON file contains the file name and a list of predictions with
    bounding boxes in `[x, y, w, h]` format (top-left corner, width, height) and
    an optional confidence score:

    ```json
    {
        "file_name": "000000001732.jpg",
        "predictions": [
            {"category_id": 0, "bbox": [223, 105, 115, 372], "score": 0.95},
            {"category_id": 26, "bbox": [204, 240, 38, 70], "score": 0.8},
            {"category_id": 28, "bbox": [35, 385, 209, 88], "score": 0.6}
        ]
    }
    ```

    </details>

---

<!-- TODO(Michal, 03/2026): Link additional docs when ready.
Moreover, you can write an adapter to load images with annotations from a custom format, see the
[TODO](../todo) for details. -->

### From an Existing Dataset

Once a dataset is populated, the data is stored in a database. It can be loaded later as follows
to skip indexing and embedding it again:

```python title="Load an Image Dataset from a Database"
import lightly_studio as ls

# Load an existing dataset from the database.
dataset = ls.ImageDataset.load()

# A helper method that creates a dataset only if it does not exist yet.
dataset = ls.ImageDataset.load_or_create()
```

All three functions `create()`, `load()`, and `load_or_create()` accept an optional `name` argument
to store multiple datasets in the database, note however that the open-source version of LightlyStudio
GUI displays only a single dataset.

!!! tip
    The `add_images_from_path(...)` and `add_samples_from_x(...)` methods skip
    duplicate images, the duplicates are detected based on absolute path.
    Therefore you can safely use them in a single script with `load_or_create()`,
    adding and embedding the images will be skipped on subsequent calls.

### Adding Annotations to Existing Images

When images are already in the dataset, the `add_annotations_from_*` methods attach
annotations without re-loading the images. Each call stores its annotations under a named
annotation source, so multiple sources (e.g. ground truth and model predictions) can be queried
and compared independently. Re-running with the same `annotation_source` appends to that annotation source;
a new `annotation_source` creates a new annotation source.

```python title="Attach annotations from multiple sources"
import lightly_studio as ls

dataset_path = ls.utils.download_example_dataset(download_dir="dataset_examples")
images_path = f"{dataset_path}/coco_subset_128_images/images"

# Load images once.
dataset = ls.ImageDataset.create()
dataset.add_images_from_path(path=images_path)

# Attach ground truth.
dataset.add_annotations_from_coco(
    annotations_json=f"{dataset_path}/coco_subset_128_images/instances_train2017.json",
    images_root=images_path,
    annotation_source="ground_truth",
)

# Attach predictions from a model (paths are illustrative).
dataset.add_annotations_from_coco(
    annotations_json="/path/to/model_A_predictions.json",
    images_root=images_path,
    annotation_source="model_A",
)
```

If the input is a COCO prediction file, LightlyStudio reads the `score` field of each annotation
and stores it as annotation confidence.

See the [API reference](../api/dataset.md#lightly_studio.ImageDataset) for `add_annotations_from_coco`, `add_annotations_from_yolo`, and `add_annotations_from_labelformat`.

## Image Dataset in the GUI

Launch the GUI from your terminal:

```shell
lightly-studio gui
```

The command starts a local web server. Click the link printed in the console - by default
`http://localhost:8001` - to open the GUI in your browser. Note that the GUI can also be
started from a Python script by calling `ls.start_gui()`.

### Grid View

The main view shows a grid of images in your dataset. From here, you can perform multiple actions:

- Use the left panel to filter the images by tags, annotations or metadata.
- Use the search bar to do similarity search by text or an image.
- Use the `Show Embeddings` button to explore the data in embedding space.
- Use the `Menu` dropdown for further actions like plugins, sampling, classification, export and more.

Refer to dedicated pages in this documentation on every feature for more details.

![Image Dataset Grid](https://storage.googleapis.com/lightly-public/studio/docs/image_dataset_grid_v1.0.0.png){ width="100%" }

### Detail View

Double-clicking on an image opens the image detail view. Here you can annotate the image,
add captions or view metadata.

![Image Detail View](https://storage.googleapis.com/lightly-public/studio/docs/image_dataset_detail_v1.0.0.png){ width="100%" }


## Image Dataset in the Python API

### ImageDataset class

The main entrypoint is the [ImageDataset class](../api/dataset.md#imagedataset).
An instance of it can be created as described above by using one of the factory methods:

```python title="Create or load an ImageDataset"
dataset = ls.ImageDataset.create()
dataset = ls.ImageDataset.load()
dataset = ls.ImageDataset.load_or_create()
```

Once samples are added to the dataset, they can be iterated over, yielding `ImageSample` objects:

```python title="Iterate over dataset samples"
for image in dataset:
    print(image.file_name)
```

### ImageSample class

[ImageSample class](../api/sample.md#imagesample) provides read and write access to the image data.

```python title="Access image data"
# Grab one sample
image = next(iter(dataset))

# Image properties
print(image.file_name)
print(image.file_path_abs)
print(image.width)
print(image.height)

# Tags
image.tags = ["tag1", "tag2"]
image.add_tag("needs_review")
image.remove_tag("needs_review")
print(image.tags)

# Captions
image.captions = ["Caption 1", "Caption 2"]
image.add_caption("Caption 3")
print(image.captions)

# Metadata
image.metadata["my_key"] = "my_value"
print(image.metadata["my_key"])

# Annotations
from lightly_studio.core.annotation import CreateObjectDetection
image.add_annotation(
    CreateObjectDetection(
        class_name="dog",
        x=10,
        y=20,
        width=30,
        height=40,
        confidence=0.9,
    )
)
for annotation in image.annotations:
    print(annotation.class_name)
```

<!-- TODO(Michal, 03/2026)
Find more details on [Tags](todo), [Captions](todo), [Metadata](todo) and [Annotations](todo)
on dedicated pages.
-->

### Querying the Dataset

Use [Dataset Query in Python](../concepts_and_tools/search_and_filter.md#query-in-python) when you need reusable subsets in code for filtering, sorting, slicing, export, or sampling. Image query expressions use `ImageSampleField`.
