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

## 💻 Installation

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

Download example datasets by cloning the example repository:

```shell
git clone https://github.com/lightly-ai/dataset_examples dataset_examples
```

=== "Image Folder"

    To run an example using an image-only dataset, create a file named `example_image.py` with the following contents:

    ```python title="example_image.py"
    import lightly_studio as ls
    from lightly_studio.utils import download_example_dataset

    dataset_path = download_example_dataset(target_dir="dataset_examples")

    # Indexes the dataset, creates embeddings and stores everything in the database. Here we only load images.
    dataset = ls.Dataset.create()
    dataset.add_samples_from_path(path=f"{dataset_path}/coco_subset_128_images/images")

    # Start the UI server on port 8001. Use env variables to change port and host:
    # LIGHTLY_STUDIO_PORT=8002
    # LIGHTLY_STUDIO_HOST=0.0.0.0
    ls.start_gui()
    ```

    Run the script with `python example_image.py`. Now you can inspect samples in the app.

=== "YOLO Object Detection"

    To run an object detection example using a YOLO dataset, create a file named `example_yolo.py` with the following contents:

    ```python title="example_yolo.py"
    import lightly_studio as ls
    from lightly_studio.utils import download_example_dataset

    # Download the example dataset (will be skipped if it already exists)
    dataset_path = download_example_dataset(target_dir="dataset_examples")

    dataset = ls.Dataset.create()
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
    `example_coco.py` with the following contents in the same directory that contains
    the `dataset_examples/` folder:

    ```python title="example_coco.py"
    import lightly_studio as ls
    from lightly_studio.utils import download_example_dataset

    # Download the example dataset (will be skipped if it already exists)
    dataset_path = download_example_dataset(target_dir="dataset_examples")

    dataset = ls.Dataset.create()
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
    dataset_path = download_example_dataset(target_dir="dataset_examples")

    dataset = ls.Dataset.create()
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

**🔍 How It Works**

1.  Your **Python script** uses the `lightly_studio` **Dataset**.
2.  The `dataset.add_samples_from_<source>` reads your images and annotations, calculates embeddings, and saves metadata to a local **`lightly_studio.db`** file (using DuckDB).
3.  `lightly_studio.start_gui()` starts a **local Backend API** server.
4.  This server reads from `lightly_studio.db` and serves data to the **UI Application** running in your browser (`http://localhost:8001`).
5.  Images are streamed directly from your disk for display in the UI.

!!! note "For Linux Users"
    We recommend using Firefox for the best experience with embedding plots, as other browsers might not render them correctly.

## 🐍 Python Interface

LightlyStudio has a powerful Python interface. You can not only index datasets but also query and manipulate them using code.

### ☁️ Using Cloud Storage
To load images directly from a cloud storage provider (like AWS S3, GCS, etc.), you must first install the required dependencies:

```py
pip install lightly-studio[cloud-storage]
```

This installs the necessary libraries: s3fs (for S3), gcsfs (for GCS), and adlfs (for Azure).
Our tool uses the fsspec library, which also supports other file systems. If you need a different provider (like FTP, SSH, etc.), you can find the required library in the [fsspec documentation](https://filesystem-spec.readthedocs.io/en/latest/api.html#other-known-implementations) and install it manually (e.g., pip install sftpfs).

**Current Support Limitations:**
* **Images:** Your images can be located in a cloud bucket (e.g., `s3://my-bucket/images/`)
* **Annotations (Labels):** Your annotation files (like `labels.json` or a `labels/` directory) must be local on your machine. Loading annotations from cloud storage is not yet supported.


### Dataset

The dataset is the main entity of the python interface. It is used to setup the data,
start the GUI, run queries and perform selections. It holds the connection to the
database file.

```py
import lightly_studio as ls

# Different loading options:
dataset = ls.Dataset.create()

# You can load data also from cloud storage
dataset.add_samples_from_path(path="s3://my-bucket/path/to/images/")

# And at any given time you can append more data (even across sources)
dataset.add_samples_from_path(path="gcs://my-bucket-2/path/to/more-images/")
dataset.add_samples_from_path(path="local-folder/some-data-not-in-the-cloud-yet")

# Load existing .db file
dataset = ls.Dataset.load()
```

### Sample

Each sample is a single data instance. The dataset stores references to all samples, allowing you to access, read, or update their attributes individually.

```py
# Iterating over the data in the dataset
for sample in dataset:
   # Access the sample: see next section

# Get all samples as list
samples = list(dataset)

# Access sample attributes
s = samples[0]
s.sample_id        # Sample ID (UUID)
s.file_name        # Image file name (str), e.g. "img1.png"
s.file_path_abs    # Full image file path (str), e.g. "full/path/img1.png"
s.tags             # The list of sample tags (list[str]), e.g. ["tag1", "tag2"]
s.metadata["key"]  # dict-like access for metadata (any)

# Set sample attributes
s.tags = {"tag1", "tag2"}
s.metadata["key"] = 123

# Adding/removing tags
s.add_tag("some_tag")
s.remove_tag("some_tag")

...
```

### Dataset Query

Dataset queries are a combination of filtering, sorting and slicing operations. For this the **Expressions** are used.

```py
from lightly_studio.core.dataset_query import AND, OR, NOT, OrderByField, SampleField

# QUERY: Define a lazy query, composed by: match, order_by, slice
# match: Find all samples that need labeling plus small samples (< 500px) that haven't been reviewed.
query = dataset.match(
    OR(
        AND(
            SampleField.width < 500,
            NOT(SampleField.tags.contains("reviewed"))
        ),
        SampleField.tags.contains("needs-labeling")
    )
)

# order_by: Sort the samples by their width descending.
query.order_by(
    OrderByField(SampleField.width).desc()
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
query.export().to_coco_object_detections()

```

#### Reference

=== "`match`"

    You can define query filters with:
    ```py
    query.match(<expression>)
    ```
    To create an expression for filtering on certain sample fields, the `SampleField.<field_name> <operator> <value>` syntax can be used. Available field names can be seen in [`SampleField`](/api/core/#lightly_studio.core.dataset_query.sample_field.SampleField).

    <details>
    <summary>Examples:</summary>

    ```py
    from lightly_studio.core.dataset_query import SampleField

    # Ordinal fields: <, <=, >, >=, ==, !=
    expr = SampleField.height >= 10            # All samples with images that are taller than 9 pixels
    expr = SampleField.width == 10             # All samples with images that are exactly 10 pixels wide
    expr = SampleField.created_at > datetime   # All samples created after datetime (actual datetime object)

    # String fields: ==, !=
    expr = SampleField.file_name == "some"     # All samples with "some" as file name
    expr = SampleField.file_path_abs != "other" # All samples that are not having "other" as file_path

    # Tags: contains()
    expr = SampleField.tags.contains("dog")    # All samples that contain the tag "dog"

    # Assign any of the previous expressions to a query:
    query.match(expr)
    ```

    </details>

    The filtering on individual fields can flexibly be combined to create more complex match expression. For this, the boolean operators [`AND`](/api/core/#lightly_studio.core.dataset_query.boolean_expression.AND), [`OR`](/api/core/#lightly_studio.core.dataset_query.boolean_expression.OR), and [`NOT`](/api/core/#lightly_studio.core.dataset_query.boolean_expression.NOT) are available. Boolean operators can arbitrarily be nested.

    <details>
    <summary>Examples:</summary>

    ```py
    from lightly_studio.core.dataset_query import AND, OR, NOT, SampleField

    # All samples with images that are between 10 and 20 pixels wide
    expr = AND(
        SampleField.width > 10,
        SampleField.width < 20
    )

    # All samples with file names that are either "a" or "b"
    expr = OR(
        SampleField.file_name == "a",
        SampleField.file_name == "b"
    )

    # All samples which do not contain a tag "dog"
    expr = NOT(SampleField.tags.contain("dog"))

    # All samples for a nested expression
    expr = OR(
        SampleField.file_name == "a",
        SampleField.file_name == "b",
        AND(
            SampleField.width > 10,
            SampleField.width < 20,
            NOT(
                SampleField.tags.contain("dog")
            ),
        ),
    )

    # Assign any of the previous expressions to a query:
    query.match(expr)
    ```
    </details>

=== "`order_by`"

    Setting the sorting of a query can done by
    ```py
    query.order_by(<expression>)
    ```

    The order expression can be defined by `OrderByField(SampleField.<field_name>).<order_direction>()`.

    <details>
    <summary>Examples:</summary>

    ```py
    from lightly_studio.core.dataset_query import OrderByField, SampleField

    # Sort the query by the width of the image in ascending order
    expr = OrderByField(SampleField.width)
    expr = OrderByField(SampleField.width).asc()

    # Sort the query by the height of the image in descending order
    expr = OrderByField(SampleField.file_name).desc()

    # Assign any of the previous expressions to a query:
    query.order_by(expr)
    ```
    </details>

=== "`slice`"

    Setting the slicing of a query can done by:
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

You can chose from various and even combined selection strategies:

=== "Diverse"

    Diversity selection can be configured directly from a `DatasetQuery`. The example below showcases a simple case of selecting diverse samples.

    ```py
    import lightly_studio as ls

    # Load your dataset
    dataset = ls.Dataset.load_or_create()
    dataset.add_samples_from_path(path="/path/to/image_dataset")

    # Select a diverse subset of 10 samples.
    dataset.query().selection().diverse(
        n_samples_to_select=10,
        selection_result_tag_name="diverse_selection",
    )

    ls.start_gui()
    ```

=== "Metadata Weighting"

    You can select samples based on the values of a metadata field. The example below showcases a simple case of selecting samples with the highest metadata value.

    ```py
    import lightly_studio as ls

    # Load your dataset
    dataset = ls.Dataset.load_or_create()
    dataset.add_samples_from_path(path="/path/to/image_dataset")
    # Compute and store 'typicality' metadata.
    dataset.compute_typicality_metadata(metadata_name="typicality")

    # Select the 5 samples with the highest 'typicality' scores.
    dataset.query().selection().metadata_weighting(
        n_samples_to_select=5,
        selection_result_tag_name="metadata_weighting_selection",
        metadata_key="typicality",
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
    dataset = ls.Dataset.load_or_create()
    dataset.add_samples_from_path(path="/path/to/image_dataset")
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
from lightly_studio.core.dataset_query import SampleField

dataset = ls.Dataset.load("my-dataset")
selected_samples = (
    dataset.match(SampleField.tags.contains("diverse_selection")).to_list()
)

with open("export.txt", "w") as f:
    for sample in selected_samples:
        f.write(f"{sample.file_path_abs}\n")
```

### API Reference

See the API Reference for more details on the python interface.
