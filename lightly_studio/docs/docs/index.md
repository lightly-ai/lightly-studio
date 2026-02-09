# Welcome to LightlyStudio!

**[LightlyStudio](https://www.lightly.ai/lightly-studio)** is an open-source tool designed to unify your data workflows from curation, annotation and management. Built with Rust for speed and efficiency, it lets you work seamlessly with datasets like COCO and ImageNet, even on a MacBook Pro with an M1 chip and 16 GB of memory.

=== "Explore"

    ![Image title](https://storage.googleapis.com/lightly-public/studio/search.gif){ width="100%"}
    Discover insights instantly with AI-powered search and smart filters.

=== "Annotate"

    ![Image title](https://storage.googleapis.com/lightly-public/studio/annotate.gif){ width="100%" }
    Create, edit, or remove annotations directly within your dataset.

=== "Embedding Plot"

    ![Image title](https://storage.googleapis.com/lightly-public/studio/embedding.gif){ width="100%" }
    Visualize your dataset’s structure in the embedding space projected with [PaCMAP](https://github.com/YingfanWang/PaCMAP).

=== "Export"

    ![Image title](https://storage.googleapis.com/lightly-public/studio/export.gif){ width="100%" }
    Export selected samples and annotations in your preferred format.

## Installation

Ensure you have **Python 3.8 or higher**. We strongly recommend using a virtual environment.

The library is OS-independent and works on Windows, Linux, and macOS.

=== "Linux/macOS"

    ```shell
    # 1. Create and activate a virtual environment (Recommended)
    python3 -m venv venv
    source venv/bin/activate

    # 2. Install LightlyStudio
    pip install lightly_studio
    ```

=== "Windows"

    ```powershell
    # 1. Create and activate a virtual environment (Recommended)
    python -m venv venv
    .\venv\Scripts\activate

    # 2. Install LightlyStudio
    pip install lightly_studio
    ```

## **Quickstart**

The examples below download the required example data the first time you run them. You can also
directly use your own image, video, or YOLO/COCO dataset.

=== "Image Folder"

    To run an example using an image-only dataset, create a file named `example_image.py` with the following contents:

    ```python title="example_image.py"
    import lightly_studio as ls
    from lightly_studio.utils import download_example_dataset

    # Download the example dataset (will be skipped if it already exists)
    dataset_path = download_example_dataset(download_dir="dataset_examples")

    # Indexes the dataset, creates embeddings and stores everything in the database. Here we only load images.
    dataset = ls.ImageDataset.create()
    dataset.add_images_from_path(path=f"{dataset_path}/coco_subset_128_images/images")

    # Start the UI server on port 8001. Use env variables to change port and host:
    # LIGHTLY_STUDIO_PORT=8002
    # LIGHTLY_STUDIO_HOST=0.0.0.0
    ls.start_gui()
    ```

    Run the script with `python example_image.py`. Now you can inspect images in the app.

    **Notebook / Colab**

    You can run the same image folder flow inside a notebook cell and embed the UI.

    [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/lightly-ai/lightly-studio/blob/main/lightly_studio/src/lightly_studio/examples/example_notebook.ipynb)

    ```python
    import lightly_studio as ls
    from lightly_studio.utils import download_example_dataset
    from lightly_studio.dataset import env

    dataset_path = download_example_dataset(download_dir="dataset_examples")
    dataset = ls.ImageDataset.create()
    dataset.add_images_from_path(path=f"{dataset_path}/coco_subset_128_images/images")

    # Colab needs 0.0.0.0 to expose the port.
    env.LIGHTLY_STUDIO_HOST = "0.0.0.0"

    ls.start_gui()
    ```

    Jupyter:

    ```python
    from IPython.display import IFrame, display

    display(IFrame(env.APP_URL, width=1000, height=800))
    ```

    Colab:

    ```python
    from google.colab import output

    output.serve_kernel_port_as_iframe(env.LIGHTLY_STUDIO_PORT, width=1000, height=800)
    ```
    
    **Tagging by Folder Structure**

    When using `dataset.add_images_from_path`, you can automatically assign tags based on your folder structure. The folder hierarchy is **relative to the `path` argument** you provide.

    For example, given a folder structure where images are classified by class:
    ```text
    my_data/
    ├── cat/
    │   ├── img1.png
    │   └── img2.png
    ├── dog/
    │   ├── img3.png
    │   └── img4.png
    └── bird/
        └── img5.png
    ```

    You can point `path` to the parent directory (`my_data/`) and **use `tag_depth=1` to enable** this auto-tagging. The code will then use the first-level subdirectories (`cat`, `dog`, `bird`) as tags.

    ```python
    dataset.add_images_from_path(path="my_data/", tag_depth=1)
    ```


=== "Video Folder"

    Create a file named `example_video.py` with the following contents:

    ```python title="example_video.py"
    import lightly_studio as ls
    from lightly_studio.core.video_dataset import VideoDataset
    from lightly_studio.utils import download_example_dataset

    # Download the example dataset (will be skipped if it already exists)
    dataset_path = download_example_dataset(download_dir="dataset_examples")

    # Create a dataset and populate it with videos.
    dataset = VideoDataset.create()
    dataset.add_videos_from_path(path=f"{dataset_path}/youtube_vis_50_videos/train/videos")

    # Start the UI server.
    ls.start_gui()
    ```

    Run the script with `python example_video.py`. Now you can inspect videos in the app.


=== "YOLO Object Detection"

    To run an object detection example using a YOLO dataset, create a file named `example_yolo.py` with the following contents:

    ```python title="example_yolo.py"
    import lightly_studio as ls
    from lightly_studio.utils import download_example_dataset

    # Download the example dataset (will be skipped if it already exists)
    dataset_path = download_example_dataset(download_dir="dataset_examples")

    dataset = ls.ImageDataset.create()
    dataset.add_samples_from_yolo(
        data_yaml=f"{dataset_path}/road_signs_yolo/data.yaml",
    )

    ls.start_gui()
    ```

    Run the script with `python example_yolo.py`. Now you can inspect samples with their assigned annotations in the app.

    <details>
    <summary>The YOLO format details:</summary>

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

    Each label file should contain YOLO format annotations (one per line):

    ```
    <class> <x_center> <y_center> <width> <height>
    ```

    Where coordinates are normalized between 0 and 1.

    </details>

=== "COCO Instance Segmentation"

    To run an instance segmentation example using a COCO dataset, create a file named
    `example_coco.py` with the following contents:

    ```python title="example_coco.py"
    import lightly_studio as ls
    from lightly_studio.utils import download_example_dataset

    # Download the example dataset (will be skipped if it already exists)
    dataset_path = download_example_dataset(download_dir="dataset_examples")

    dataset = ls.ImageDataset.create()
    dataset.add_samples_from_coco(
        annotations_json=f"{dataset_path}/coco_subset_128_images/instances_train2017.json",
        images_path=f"{dataset_path}/coco_subset_128_images/images",
        annotation_type=ls.AnnotationType.INSTANCE_SEGMENTATION,
    )

    ls.start_gui()
    ```

    Run the script via `python example_coco.py`. Now you can inspect samples with their assigned annotations in the app.

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

    To run a caption example using a COCO dataset, create a file named `example_coco_captions.py` with the following contents:

    ```python title="example_coco_captions.py"
    import lightly_studio as ls
    from lightly_studio.utils import download_example_dataset

    # Download the example dataset (will be skipped if it already exists)
    dataset_path = download_example_dataset(download_dir="dataset_examples")

    dataset = ls.ImageDataset.create()
    dataset.add_samples_from_coco_caption(
        annotations_json=f"{dataset_path}/coco_subset_128_images/captions_train2017.json",
        images_path=f"{dataset_path}/coco_subset_128_images/images",
    )

    ls.start_gui()
    ```

    Run the script with `python example_coco_captions.py`. Now you can inspect samples with their assigned captions in the app.

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

---

**How It Works**

1.  Your **Python script** uses the `lightly_studio` **Dataset**.
2.  The `dataset.add_<samples>_from_<source>` reads your images and annotations, calculates embeddings, and saves metadata to a local **`lightly_studio.db`** file (using DuckDB).
3.  `lightly_studio.start_gui()` starts a **local Backend API** server.
4.  This server reads from `lightly_studio.db` and serves data to the **UI Application** running in your browser (`http://localhost:8001`).
5.  Images are streamed directly from your disk for display in the UI.

!!! note "For Linux Users"
    We recommend using Firefox for the best experience with embedding plots, as other browsers might not render them correctly.

## Python Interface

LightlyStudio has a powerful Python interface. You can not only index datasets but also query and manipulate them using code.

### Dataset

The dataset is the main entity of the python interface. It is used to setup the data,
start the GUI, run queries and perform selections. It holds the connection to the
database file. Every dataset writes its metadata, tags, annotations, captions, and embeddings into a DuckDB file named `lightly_studio.db`.

```py
import lightly_studio as ls

# Different loading options:
dataset = ls.ImageDataset.create()

# You can load data directly from a folder
dataset.add_images_from_path(path="local-folder/some-local-data")

# Or you can load more data at a later point (even across sources such as cloud)
dataset.add_images_from_path(path="local-folder/some-data-not-loaded-yet")
dataset.add_images_from_path(path="gcs://my-bucket-2/path/to/more-images/")

# You can also load a dataset from an .db file (default uses the `lightly_studio.db` file in the working directory)
dataset = ls.ImageDataset.load()
```

To store the DuckDB file elsewhere (for example, on a larger external disk or to maintain isolated projects), configure the database manager before creating/loading any datasets:

```python
from lightly_studio import db_manager

db_manager.connect(db_file="~/lightly_data/my-db-path.db")
```

!!! note
    Within the `.db` file all paths are stored as absolute paths. This allows the software to fetch data for visualization even if you move the .db file around.


#### Reusing Datasets

Restarting the same Python script will reopen the GUI with the previous state as long as you call `ImageDataset.load` or `ImageDataset.load_or_create` with the same name.

```python title="reuse_dataset.py"
from __future__ import annotations

import lightly_studio as ls

DATASET_NAME = "sport_shooting"
IMAGE_DIRS = ["data/primary_images", "data/new_images_later"]

# Everything persists inside lightly_studio.db automatically.
dataset = ls.ImageDataset.load_or_create(name=DATASET_NAME)

# Only new samples are added by `add_images_from_path`
for image_dir in IMAGE_DIRS:
    dataset.add_images_from_path(path=image_dir)

ls.start_gui()
```

- When you rerun the script later, only new files are indexed. Existing embeddings and annotations remain untouched; embeddings are generated only for the new samples (set `embed=False` to skip).
- Manual labels created in the GUI, metadata changed via Python, and tags assigned anywhere are all stored in `lightly_studio.db`, so you can stop/start the process at will.
- External files such as images/videos (.jpg, .png files etc.) remain in the original folders; keep them accessible so the GUI can display them when you reopen the dataset.

#### Using Cloud Storage

To load images directly from a cloud storage provider (like AWS S3, GCS, etc.), first install the required dependencies:

```shell
pip install "lightly-studio[cloud-storage]"
```

This installs [s3fs](https://github.com/fsspec/s3fs) (for S3), [gcsfs](https://github.com/fsspec/gcsfs) (for GCS), and [adlfs](https://github.com/fsspec/adlfs) (for Azure). For other providers, see the [fsspec documentation](https://filesystem-spec.readthedocs.io/en/latest/api.html#other-known-implementations).

**Example: Loading images from S3**

```py
import lightly_studio as ls

dataset = ls.ImageDataset.create(name="s3_dataset")
dataset.add_images_from_path(path="s3://my-bucket/images/")

ls.start_gui()
```

The images remain in S3 and are streamed to the UI when displayed. Make sure your AWS credentials are configured (via environment variables or `~/.aws/credentials`).

**Current Limitations:**

!!! warning "Cloud Storage Limitation"
    Cloud storage is only supported for image-only datasets using `add_images_from_path()` or when manually indexing the data with annotations. When loading annotated datasets with `add_samples_from_coco()` or `add_samples_from_yolo()`, both images and annotation files must be stored locally for now. The same is true for video files, they can be only loaded locally.


### Sample

Each sample is a single data instance. The dataset stores references to all samples, allowing you to access, read, or update their attributes individually.

```py
import lightly_studio as ls

dataset = ls.ImageDataset.load_or_create(name="my_dataset")
dataset.add_images_from_path(path="path/to/images")

# Iterating over the data in the dataset
for sample in dataset:
    # Access sample attributes
    sample.sample_id        # Sample ID (UUID)
    sample.file_name        # Image file name (str), e.g. "img1.png"
    sample.file_path_abs    # Full image file path (str), e.g. "full/path/img1.png"
    sample.tags             # The set of sample tags (set[str]), e.g. {"tag1", "tag2"}
    sample.metadata         # Dict-like access to custom metadata

    # Adding/removing tags
    sample.add_tag("needs_review")
    sample.remove_tag("needs_review")
```

**Adding metadata to samples**

You can attach custom metadata to samples, for example sensor data from a robotics application:

```py
for sample in dataset:
    sample.metadata["camera_id"] = "front_left"
    sample.metadata["gps_lat"] = 47.3769
    sample.metadata["gps_lon"] = 8.5417
    sample.metadata["speed"] = 12.5
    sample.metadata["weather"] = "sunny"
```

**Accessing annotations**

You can access annotations of each sample. They can be created in the GUI or imported, e.g. from the COCO format, see the [COCO Instance Segmentation](#quickstart) example above. In the next section [Indexing with Predictions](#indexing-with-predictions) an example of creating annotations from Python is provided.

```py
from lightly_studio.core.annotation import ObjectDetectionAnnotation

for sample in dataset:
    for annotation in sample.annotations:
        if isinstance(annotation, ObjectDetectionAnnotation):
            print(annotation.x, annotation.y, annotation.width, annotation.height)
```

There are 4 different types: `ClassificationAnnotation`, `InstanceSegmentationAnnotation`, `ObjectDetectionAnnotation` and `SemanticSegmentationAnnotation`.

**Adding annotations**

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

There are also `CreateClassification`, `CreateInstanceSegmentation`, and `CreateSemanticSegmentation` classes for other annotation types.

For segmentation annotations, it is recommended to use the `from_binary_mask` method, which automatically handles the bounding box and mask encoding from a 2D numpy array:

```python
import numpy as np
from lightly_studio.core.annotation import CreateSemanticSegmentation

# A 2D numpy array representing the binary mask (1 for foreground, 0 for background)
mask = np.array([
    [0, 0, 0, 0],
    [0, 1, 1, 0],
    [0, 1, 1, 0],
    [0, 0, 0, 0],
])

sample.add_annotation(
    CreateSemanticSegmentation.from_binary_mask(
        label="car",
        binary_mask=mask,
        confidence=0.85,
    )
)
```

Alternatively, you can manually provide the bounding box and mask encoding:

```python
from lightly_studio.core.annotation import CreateSemanticSegmentation

sample.add_annotation(CreateSemanticSegmentation(
    label="car",
    confidence=0.85,
    x=2,
    y=3,
    width=3,
    height=2,
    segmentation_mask=[17, 2, 3, 1, 2],
))
```

**Binary Mask Format**

For segmentation annotations (`CreateSemanticSegmentation`, `CreateInstanceSegmentation`), the `segmentation_mask` is expected to be a list of integers representing the binary mask in a row-wise Run-Length Encoding (RLE) format.

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
            confidence=pred["conf"],  # Model confidence, must be between 0.0 and 1.0
            x=pred["x"],
            y=pred["y"],
            width=pred["w"],
            height=pred["h"],
        )
    )
```

!!! note "Embeddings not supported"
    Manual indexing does not generate embeddings. Features like similarity search and embedding plots will not be available for manually indexed samples.

### Dataset Query

You can programmatically filter samples by attributes (e.g., image size, tags), sort them, and select subsets. This is useful for creating training/validation splits, finding specific samples, or exporting filtered data.

!!! tip "GUI Support"
    These filtering and querying operations can also be performed directly for image datasets in the GUI using the search and filter panels.

```py
from lightly_studio.core.dataset_query import AND, OR, NOT, OrderByField, ImageSampleField

# QUERY: Define a lazy query, composed by: match, order_by, slice
# match: Find all samples that need labeling plus small samples (< 500px) that haven't been reviewed.
query = dataset.match(
    OR(
        AND(
            ImageSampleField.width < 500,
            NOT(ImageSampleField.tags.contains("reviewed"))
        ),
        ImageSampleField.tags.contains("needs-labeling")
    )
)

# order_by: Sort the samples by their width descending.
query.order_by(
    OrderByField(ImageSampleField.width).desc()
)

# slice: Extract a slice of samples.
query[10:20]

# chaining: The query can also be constructed in chained way
query = dataset.match(...).order_by(...)[...]

# Ways to consume the query
# Tag this subset for easy filtering in the UI.
query.add_tag("needs-review")

# Iterate over resulting samples
for sample in query:
    # Access the sample: see previous section

# Collect all resulting samples as list
samples = query.to_list()

# Export all resulting samples in coco format
dataset.export(query).to_coco_object_detections()

```

For video, use `VideoSampleField` instead. For example, the following code works for video.
```py
from lightly_studio.core.dataset_query import AND, OR, NOT, OrderByField, VideoSampleField

# QUERY: Define a lazy query, composed by: match, order_by, slice
# match: Find all samples that need labeling plus small samples (< 500px) that have small FPS.
query = dataset.match(
    OR(
        AND(
            VideoSampleField.width < 500,
            NOT(VideoSampleField.fps >= 30)
        ),
        VideoSampleField.tags.contains("needs-labeling")
    )
)

# order_by: Sort the samples by their width descending.
query.order_by(
    OrderByField(VideoSampleField.width).desc()
)
```

#### Reference

=== "`match`"

    You can define query filters with:
    ```py
    query.match(<expression>)
    ```
    To create an expression for filtering on certain sample fields, the `ImageSampleField.<field_name> <operator> <value>` syntax can be used. Available field names can be seen in [`ImageSampleField`](/api/core/#lightly_studio.core.dataset_query.image_sample_field.ImageSampleField).

    <details>
    <summary>Examples:</summary>

    ```py
    from lightly_studio.core.dataset_query import ImageSampleField

    # Ordinal fields: <, <=, >, >=, ==, !=
    expr = ImageSampleField.height >= 10            # All samples with images that are taller than 9 pixels
    expr = ImageSampleField.width == 10             # All samples with images that are exactly 10 pixels wide
    expr = ImageSampleField.created_at > datetime   # All samples created after datetime (actual datetime object)

    # String fields: ==, !=
    expr = ImageSampleField.file_name == "some"     # All samples with "some" as file name
    expr = ImageSampleField.file_path_abs != "other" # All samples that are not having "other" as file_path

    # Tags: contains()
    expr = ImageSampleField.tags.contains("dog")    # All samples that contain the tag "dog"

    # Assign any of the previous expressions to a query:
    query.match(expr)
    ```

    </details>

    The filtering on individual fields can flexibly be combined to create more complex match expression. For this, the boolean operators [`AND`](/api/core/#lightly_studio.core.dataset_query.boolean_expression.AND), [`OR`](/api/core/#lightly_studio.core.dataset_query.boolean_expression.OR), and [`NOT`](/api/core/#lightly_studio.core.dataset_query.boolean_expression.NOT) are available. Boolean operators can arbitrarily be nested.

    <details>
    <summary>Examples:</summary>

    ```py
    from lightly_studio.core.dataset_query import AND, OR, NOT, ImageSampleField

    # All samples with images that are between 10 and 20 pixels wide
    expr = AND(
        ImageSampleField.width > 10,
        ImageSampleField.width < 20
    )

    # All samples with file names that are either "a" or "b"
    expr = OR(
        ImageSampleField.file_name == "a",
        ImageSampleField.file_name == "b"
    )

    # All samples which do not contain a tag "dog"
    expr = NOT(ImageSampleField.tags.contains("dog"))

    # All samples for a nested expression
    expr = OR(
        ImageSampleField.file_name == "a",
        ImageSampleField.file_name == "b",
        AND(
            ImageSampleField.width > 10,
            ImageSampleField.width < 20,
            NOT(
                ImageSampleField.tags.contains("dog")
            ),
        ),
    )

    # Assign any of the previous expressions to a query:
    query.match(expr)
    ```
    </details>

=== "`order_by`"

    Setting the sorting of a query can be done by
    ```py
    query.order_by(<expression>)
    ```

    The order expression can be defined by `OrderByField(ImageSampleField.<field_name>).<order_direction>()`.

    <details>
    <summary>Examples:</summary>

    ```py
    from lightly_studio.core.dataset_query import OrderByField, ImageSampleField

    # Sort the query by the width of the image in ascending order
    expr = OrderByField(ImageSampleField.width)
    expr = OrderByField(ImageSampleField.width).asc()

    # Sort the query by the file name in descending order
    expr = OrderByField(ImageSampleField.file_name).desc()

    # Assign any of the previous expressions to a query:
    query.order_by(expr)
    ```
    </details>

=== "`slice`"

    Setting the slicing of a query can be done by:
    ```py
    query.slice(<offset>, <limit>)
    # OR
    query[<offset>:<stop>]
    ```

    <details>
    <summary>Examples:</summary>

    ```py
    # Slice 2:5
    query.slice(offset=2, limit=3)
    query[2:5]

    # Slice :5
    query.slice(limit=5)
    query[:5]

    # Slice 5:
    query.slice(offset=5)
    query[5:]
    ```
    </details>

---

### Selection

LightlyStudio offers a premium feature to perform automatized data selection. Selecting the right subset of your data can save labeling cost and training time while improving model quality.

**Prerequisite:** The selection functionality requires a valid LightlyStudio license key.
Set the `LIGHTLY_STUDIO_LICENSE_KEY` environment variable before using selection features:

=== "Linux/macOS"

    ```bash
    export LIGHTLY_STUDIO_LICENSE_KEY="license_key_here"
    ```

=== "Windows"

    ```powershell
    $env:LIGHTLY_STUDIO_LICENSE_KEY="license_key_here"
    ```

You can choose from various and even combined selection strategies:

=== "Diverse"

    Diversity selection can be configured directly from a `DatasetQuery`. The example below showcases a simple case of selecting diverse samples.

    ```py
    import lightly_studio as ls

    # Load your dataset
    dataset = ls.ImageDataset.load_or_create()
    dataset.add_images_from_path(path="/path/to/image_dataset")

    # Select a diverse subset of 10 samples.
    dataset.query().selection().diverse(
        n_samples_to_select=10,
        selection_result_tag_name="diverse_selection",
    )

    ls.start_gui()
    ```

=== "Metadata Weighting"

    You can select samples based on the values of a metadata field. The example below showcases a simple case of selecting samples with the highest metadata value (typicality). Typicality is calculated for the given dataset first.

    ```py
    import lightly_studio as ls

    # Load your dataset
    dataset = ls.ImageDataset.load_or_create()
    dataset.add_images_from_path(path="/path/to/image_dataset")
    # Compute and store 'typicality' metadata.
    dataset.compute_typicality_metadata(metadata_name="typicality")

    # Select the 5 samples with the highest 'typicality' scores.
    dataset.query().selection().metadata_weighting(
        n_samples_to_select=5,
        selection_result_tag_name="metadata_weighting_selection",
        metadata_key="typicality",
    )
    ```


=== "Similarity Weighting"

    You can select samples based on their similarity to a specific subset of your data. The example below shows how to select samples that are most similar to a set of pre-tagged images.

    ```py
    import lightly_studio as ls

    # Load your dataset
    dataset = ls.ImageDataset.load_or_create()
    dataset.add_images_from_path(path="/path/to/image_dataset")

    # First, define a query set by tagging some samples.
    # For example, let's tag the first 5 samples.
    dataset[:5].add_tag("my_query_samples")

    # Compute similarity to the tagged samples and store it as
    # 'similarity_to_query' metadata.
    dataset.compute_similarity_metadata(
        query_tag_name="my_query_samples",
        metadata_name="similarity_to_query"
    )

    # Select the 10 samples most similar to the query set.
    dataset.query().selection().metadata_weighting(
        n_samples_to_select=10,
        selection_result_tag_name="similar_to_query_selection",
        metadata_key="similarity_to_query",
    )
    ```


=== "Class Balancing"

    You can select samples based on the distribution of object classes (annotations). This is useful for fixing class imbalance, e.g., ensuring you have enough "pedestrians" in a driving dataset.

    **Note:** This strategy requires the dataset to have annotations, e.g., loaded via `add_samples_from_coco` or `add_samples_from_yolo`.

    ```py
    import lightly_studio as ls

    # Load your dataset
    dataset = ls.ImageDataset.load_or_create()

    # Option 1: Balance classes uniformly (e.g. equal number of cats and dogs)
    dataset.query().selection().annotation_balancing(
        n_samples_to_select=50,
        selection_result_tag_name="balanced_uniform",
        target_distribution="uniform",
    )

    # Option 2: Define a specific target distribution (e.g. 20% cat, 80% dog)
    dataset.query().selection().annotation_balancing(
        n_samples_to_select=50,
        selection_result_tag_name="balanced_custom",
        target_distribution={"cat": 0.2, "dog": 0.8},
    )
    ```

=== "Multiple Strategies"

    You can configure multiple strategies, the selection takes into account all of them at the same time, weighted by the `strength` parameter.

    ```py
    import lightly_studio as ls
    from lightly_studio.selection.selection_config import (
        MetadataWeightingStrategy,
        EmbeddingDiversityStrategy,
    )

    # Load your dataset
    dataset = ls.ImageDataset.load_or_create()
    dataset.add_images_from_path(path="/path/to/image_dataset")
    # Compute typicality and store it as `typicality` metadata
    dataset.compute_typicality_metadata(metadata_name="typicality")

    # Select 10 samples by combining typicality and diversity, diversity having double the strength.
    dataset.query().selection().multi_strategies(
        n_samples_to_select=10,
        selection_result_tag_name="multi_strategy_selection",
        selection_strategies=[
            MetadataWeightingStrategy(metadata_key="typicality", strength=1.0),
            EmbeddingDiversityStrategy(embedding_model_name="my_model_name", strength=2.0),
        ],
    )
    ```

**Exporting Selected Samples**

The selected sample paths can be exported via the GUI, or by a script:

```py
import lightly_studio as ls
from lightly_studio.core.dataset_query import ImageSampleField

dataset = ls.ImageDataset.load("my-dataset")
selected_samples = (
    dataset.match(ImageSampleField.tags.contains("diverse_selection")).to_list()
)

with open("export.txt", "w") as f:
    for sample in selected_samples:
        f.write(f"{sample.file_path_abs}\n")
```

### API Reference

See the [Python API](api/dataset.md) for more details on the python interface.

## Plugins

LightlyStudio offers the possibility to extend its functionality by using plugins. Users can define their own plugins or use available ones.

The LightlyStudio operator plugin makes it possible to call a python function in the backend through a dialog in the graphical user interface (GUI) alias frontend. After you register an operator through the Python API, the GUI lists it automatically. For operators using the builtin parameter types, the dialog in the GUI is generated and rendered automatically.

### Operator Plugin

An operator plugin is defined by the following attributes of the [`BaseOperator`](api/plugin/#lightly_studio.plugins.base_operator.BaseOperator) schema:

- name: The name of the operator that will also be used in the GUI.
- description: A detailed description of what the operator does.
- parameters: A list of inputs exposed in the GUI. Supported parameter types are documented under [`Parameter`](api/plugin/#parameter)
- execute: The method that is used to execute the actual action. It will receive the parameters from the GUI.


#### Hello World 

An example `Hello World" operator plugin looks this:

```python title="greeting_operator.py"
from dataclasses import dataclass

from lightly_studio.plugins.base_operator import BaseOperator, OperatorResult
from lightly_studio.plugins.parameter import StringParameter


@dataclass
class GreetingOperator(BaseOperator):
    name: str = "GreetingOperator"
    description: str = "This operator greet you"

    @property
    def parameters(self):
        return [
            StringParameter(
                name="name",
                required=True,
                default="beautiful and smart person",
                description="your name"
            ),
        ]

    def execute(self, *, session, collection_id, parameters):
        your_name = parameters.get("name", "")
        return OperatorResult(success=True, message=f"Hello {your_name}!")
```

To make an operator known to the application, you have to register it. For this you need to extend our main execution .py file:

```python title="example_operator.py"
import lightly_studio as ls
from lightly_studio.plugins.operator_registry import operator_registry
from lightly_studio.utils import download_example_dataset
from greeting_operator import GreetingOperator

dataset_path = download_example_dataset(download_dir="dataset_examples")

dataset = ls.ImageDataset.create()
dataset.add_images_from_path(path=f"{dataset_path}/coco_subset_128_images/images")

# Register the operator to make it available to the application
operator_registry.register(GreetingOperator())

ls.start_gui()
```

After launching the GUI, the new plugin appears in the menu at the top-right corner.

![Hello World Plugin](https://storage.googleapis.com/lightly-public/studio/plugin_hello_world.gif){ width="100%" }

#### LightlyTrain Object Detection

In this example we create an auto-labeling operator plugin powered by LightlyTrain, so make sure `lightly-train` is installed via `pip install lightly-train`. Compared to the Hello World example, this operator plugin introduces two inputs: the model name and the confidence threshold used for predictions. These parameters let you choose a pre-trained LightlyTrain model and control how confident detections must be before they are written back to LightlyStudio.

```python title="lightly_train_auto_label_od_operator.py"
from dataclasses import dataclass

import lightly_train
from PIL import Image
from lightly_train._commands.predict_task_helpers import prepare_coco_entries as prepare_entries

from lightly_studio.models.annotation.annotation_base import AnnotationCreate, AnnotationType
from lightly_studio.models.annotation_label import AnnotationLabelCreate
from lightly_studio.plugins.base_operator import BaseOperator, OperatorResult
from lightly_studio.plugins.parameter import FloatParameter, StringParameter
from lightly_studio.resolvers import annotation_label_resolver, annotation_resolver, image_resolver


def _preload_label_map(session, dataset_id, class_names):
    """Pre-creates all necessary labels in the DB and returns a lookup map.

    Args:
        session: Database session.
        class_names: List of class names the model supports (e.g. ['car', 'person']).

    Returns:
        A dictionary mapping label names to their DB UUIDs.
    """
    label_map = {}

    for name in class_names:
        # Check if label exists in db
        label = annotation_label_resolver.get_by_label_name(session=session, label_name=name)

        # Create if missing
        if label is None:
            label_create = AnnotationLabelCreate(dataset_id=dataset_id, annotation_label_name=name)
            label = annotation_label_resolver.create(session=session, label=label_create)

        label_map[name] = label.annotation_label_id

    return label_map

@dataclass
class LightlyTrainAutoLabelingODOperator(BaseOperator):
    name: str = "LightlyTrain: OD auto-labeling"
    description: str = "This plugin allows to use pre-trained LightlyTrain models to perform auto-labeling for Object Detection."

    @property
    def parameters(self):
        return [
            StringParameter(
                name="Model",
                required=True,
                description="The name of the pre-trained model to be used.",
                default="dinov3/convnext-tiny-ltdetr-coco"
            ),
            FloatParameter(
                name="Threshold",
                default=0.4,
                description="The confidence threshold to be applied to the predictions."
            ),
        ]

    def execute(self, *, session, collection_id, parameters):
        try:
            model = lightly_train.load_model(parameters["Model"])
        except ValueError as e:
            return OperatorResult(success=False, message=f"Model load failed: {str(e)}")
        
        if (parameters["Threshold"] > 1.0) or (parameters["Threshold"] < 0.0):
            return OperatorResult(success=False, message="Threshold must be in range 0.0 to 1.0")

        raw_classes = getattr(model, "classes", {})
        label_map = _preload_label_map(session, collection_id, list(raw_classes.values()))

        # Running inference
        annotations_buffer = []
        samples = image_resolver.get_all_by_collection_id(session=session, collection_id=collection_id)
        for sample in samples.samples:
            image = Image.open(sample.file_path_abs).convert("RGB")

            preds = model.predict(image, threshold=parameters["Threshold"])
            entries = prepare_entries(predictions=preds, image_size=(sample.width, sample.height))

            for entry in entries:
                annotations_buffer.append(
                    AnnotationCreate(
                        parent_sample_id=sample.sample_id,
                        annotation_label_id=label_map[raw_classes[entry["category_id"]]],
                        annotation_type=AnnotationType.OBJECT_DETECTION,
                        x=int(entry["bbox"][0]),
                        y=int(entry["bbox"][1]),
                        width=int(entry["bbox"][2]),
                        height=int(entry["bbox"][3]),
                        confidence=entry["score"],
                    )
                )

        annotation_resolver.create_many(
            session=session,
            parent_collection_id=collection_id,
            annotations=annotations_buffer,
        )
        total_created = len(annotations_buffer)

        return OperatorResult(
            success=True, message=f"Auto-labeling complete. Added {total_created} annotations."
        )

```

```python title="example_operator_auto_label.py"
import lightly_studio as ls
from lightly_studio.plugins.operator_registry import operator_registry
from lightly_studio.utils import download_example_dataset
from lightly_train_auto_label_od_operator import LightlyTrainAutoLabelingODOperator

dataset_path = download_example_dataset(download_dir="dataset_examples")

dataset = ls.ImageDataset.create()
dataset.add_images_from_path(path=f"{dataset_path}/coco_subset_128_images/images")

# Register the operator to make it available to the application
operator_registry.register(LightlyTrainAutoLabelingODOperator())

ls.start_gui()
```

![LightlyTrain plugin](https://storage.googleapis.com/lightly-public/studio/plugin_LightlyTrain_autoOD.gif
){ width="100%" }
