# Python API

LightlyStudio has a powerful Python interface. You can not only index datasets but also query and manipulate them using code.

## Dataset

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


### Reusing Datasets

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
- External files such as images/videos (.jpg, .png, .mp4 files etc.) remain in their original location; keep them accessible so the GUI can display them when you reopen the dataset.

### Using Cloud Storage

To load images or videos directly from a cloud storage provider (like AWS S3, GCS, etc.), first install the required dependencies:

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

**Example: Loading videos from S3**

```py
import lightly_studio as ls

dataset = ls.VideoDataset.create(name="s3_video_dataset")
dataset.add_videos_from_path(path="s3://my-bucket/videos/")

ls.start_gui()
```

Files remain in the remote storage and are streamed to the UI on demand. Make sure your cloud credentials are configured for the selected provider.

**Current Limitations:**

!!! warning "Cloud Storage Limitation"
    Cloud storage is supported for raw media folders via `add_images_from_path()` and `add_videos_from_path()`, and for COCO object detection and instance segmentation imports via `add_samples_from_coco()`. Other dataset importers still expect local files.


## Sample

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

### Accessing annotations

You can access annotations of each sample. They can be created in the GUI or imported, e.g. from the COCO format, see the [COCO Instance Segmentation](../#quickstart) example. In the next section [Indexing with Predictions](#indexing-with-predictions) an example of creating annotations from Python is provided.

```py
from lightly_studio.core.annotation import ObjectDetectionAnnotation

for sample in dataset:
    for annotation in sample.annotations:
        if isinstance(annotation, ObjectDetectionAnnotation):
            print(annotation.x, annotation.y, annotation.width, annotation.height)
```

There are 4 different types: `ClassificationAnnotation`, `InstanceSegmentationAnnotation`, `ObjectDetectionAnnotation` and `SemanticSegmentationAnnotation`.

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
        confidence=0.85, # optional
    )
)
```

Alternatively, you can provide the mask encoding using the `from_rle_mask` method:

```python
from lightly_studio.core.annotation import CreateSemanticSegmentation

# E.g., for a 2x4 mask:
# [[0, 1, 1, 0],
#  [1, 1, 1, 1]]
# A row-wise Run-Length Encoding (RLE) mask is: [1, 2, 1, 4]
sample.add_annotation(
    CreateSemanticSegmentation.from_rle_mask(
        label="car",
        segmentation_mask=[1, 2, 1, 4],
        # `sample` could be ImageSample or another 2D sample, such as a video frame
        sample_2d=sample,
        confidence=0.85, # optional
    )
)
```


??? note "Binary Mask Format"

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

## Indexing with Predictions

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

## Dataset Query

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

### Reference

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

## Selection

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

## API Reference

See the menu on the left for the full API reference of the Python interface.
