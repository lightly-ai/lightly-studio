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
supported, see [Using Cloud Storage](../api/index.md#using-cloud-storage) for more details.

Added images are automatically embedded so that embedding plot and image search are enabled.
To skip embedding, pass `embed=False` to the method.

The method supports additional arguments, e.g. you can pass `tag_depth=1` to add the image parent
folder name as a tag to each sample. See the [API reference](../api/dataset.md#lightly_studio.ImageDataset.add_images_from_path) for full details.

### From an Annotation Format

ImageDataset class exposes methods to load images with annotations from a number of
standard formats:

- YOLO Object Detections
- COCO Object Detections
- COCO Instance Segmentations
- COCO Captions
- Pascal VOC Semantic Segmentations
- Lightly Object Detections

See [API reference](../api/dataset.md#lightly_studio.ImageDataset) for full details.

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
      also instance segmentation information, however we load just the bounding boxes.

    </details>

=== "COCO Instance Segmentations"


    ```python
    import lightly_studio as ls

    # Download the example dataset (will be skipped if it already exists)
    dataset_path = ls.utils.download_example_dataset(download_dir="dataset_examples")

    dataset = ls.ImageDataset.create()
    dataset.add_samples_from_coco(
        annotations_json=f"{dataset_path}/coco_subset_128_images/instances_train2017.json",
        images_path=f"{dataset_path}/coco_subset_128_images/images",
        annotation_type=ls.AnnotationType.INSTANCE_SEGMENTATION,
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

    COCO uses a single JSON file containing all captions. The format consists of three main components:

    - Images: Defines metadata for each image in the dataset.
    - Annotations: Defines the captions.

    </details>

=== "PascalVOC Semantic Segmentations"

    TODO

=== "Lightly Object Detections"

    TODO

---

<!-- TODO(Michal, 03/2026): Link additional docs when ready.
Moreover, you can write an adapter to load images with annotations from a custom format, see the
[TODO](../todo) for details. -->

### From a Pre-Existing Dataset

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
    The `add_images_from_path(...)` and `add_samples_from_x(...)` methods skip adding images with
    duplicate paths. Therefore you can safely use them in a single script with `load_or_create()`,
    adding and embedding the images will be skipped on subsequent calls.


## Image Dataset in the GUI

<!-- TODO(Michal, 03/2026): Add content. -->

## Image Dataset in the Python API

<!-- TODO(Michal, 03/2026): Add content. -->
