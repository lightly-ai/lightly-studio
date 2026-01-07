<p align="center">
  <a href="https://lightly.ai/lightly-studio"> 
    <img src="https://cdn.prod.website-files.com/62cd5ce03261cba217188442/66dac501a8e9a90495970876_Logo%20dark-short-p-800.png" height="50" alt="LightlyStudio logo" />
  </a>
</p>
<p align="center"><strong>Curate, Annotate, and Manage Your Data in LightlyStudio.</strong></p>
<p align="center">
  <a href="https://pypi.org/project/lightly-studio">
    <img src="https://img.shields.io/pypi/pyversions/lightly-studio" alt="PyPI python" />
  </a>
  <a href="https://pypi.org/project/lightly-studio">
    <img src="https://badge.fury.io/py/lightly-studio.svg" alt="PyPI version" />
  </a>
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/License-Apache%202.0-blue.svg" alt="License" />
  </a>
  <a href="https://docs.lightly.ai/studio">
    <img src="https://img.shields.io/badge/Docs-blue" alt="Docs" />
  </a>
  <a href="https://colab.research.google.com/github/lightly-ai/lightly-studio/blob/main/lightly_studio/src/lightly_studio/examples/example_notebook.ipynb">
    <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab" />
  </a>
</p>

---

# Welcome to LightlyStudio!

We at **[Lightly](https://lightly.ai)** created **[LightlyStudio](https://www.lightly.ai/lightly-studio)**, an open-source tool designed to unify your data workflows from curation, annotation and management in a single tool. Since we're big fans of Rust we used it to speed things up. You can work with COCO and ImageNet on a Macbook Pro with M1 and 16GB of memory!

<p align="center">
  <img alt="LightlyStudio Overview" src="https://storage.googleapis.com/lightly-public/studio/studio_overview.gif" width="70%">
  <br/>
  <em>Curate, Annotate, and Manage Your Data in LightlyStudio.</em>
</p>

## 💻 Installation

Runs on **Python 3.8 or higher** on Windows, Linux and MacOS.

```shell
pip install lightly-studio
```


Supported features: 

| Feature / Task | Classification | Detection | Sem. Segmentation | Inst. Segmentation | Captions (img+text) | Video | Keypoints | 3D Point Clouds | Text |
|----------------|:--------------:|:---------:|:---------------------:|:---------------------:|:-------------:|:-----:|:---------:|:---------------:|:---------:|
| Visualisation | 🛠️ | ✅ | 🛠️ | ✅ | ✅ | ✅ | ❌ | 🛠️ | 🛠️ |
| Filtering | 🛠️ | ✅ | ✅ | 🛠️ | ✅ | ✅ | ❌ | 🛠️ | 🛠️ |
| Labeling | 🛠️ | ✅ |🛠️ | 🛠️ | ✅ | 🛠️ | ❌ | ❌ | 🛠️ |

✅ - supported<br>
🛠️ - support in progress (ETA <2 months)<br>
❌ - not yet supported


## 🚀 Quickstart

The examples below download the required example data the first time you run them. You can also
directly use your own image, video, or YOLO/COCO dataset.

### Image Folder
To run an example using an image-only dataset, create a file named `example_image.py` with the following contents:

```python title="example_image.py"
import lightly_studio as ls
from lightly_studio.utils import download_example_dataset

# Download the example dataset (will be skipped if it already exists)
dataset_path = download_example_dataset(download_dir="dataset_examples")

# Indexes the dataset, creates embeddings and stores everything in the database. Here we only load images.
dataset = ls.Dataset.create()
dataset.add_images_from_path(path=f"{dataset_path}/coco_subset_128_images/images")

# Start the UI server on localhost:8001.
# Use env variables LIGHTLY_STUDIO_HOST and LIGHTLY_STUDIO_PORT to customize it.
ls.start_gui()
```

Run the script with `python example_image.py`. Now you can inspect samples in the app.

### Notebook / Colab
For Jupyter or Google Colab, you can run the same image folder flow inside a notebook cell and embed the UI.

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/lightly-ai/lightly-studio/blob/main/lightly_studio/src/lightly_studio/examples/example_notebook.ipynb)

```python
import lightly_studio as ls
from lightly_studio.utils import download_example_dataset
from lightly_studio.dataset import env

dataset_path = download_example_dataset(download_dir="dataset_examples")
dataset = ls.Dataset.create()
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

When using `dataset.add_images_from_path`, you can automatically assign tags based on your folder
structure. The folder hierarchy is **relative to the `path` argument** you provide. See
our [documentation](https://docs.lightly.ai/studio/) for more information.

```python
dataset.add_images_from_path(path="my_data/", tag_depth=1)
```

### Video Folder

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

### YOLO Object Detection

To run an object detection example using a [YOLO](https://labelformat.com/formats/object-detection/yolov8/) dataset, create a file named `example_yolo.py`:

```python title="example_yolo.py"
import lightly_studio as ls
from lightly_studio.utils import download_example_dataset

# Download the example dataset (will be skipped if it already exists)
dataset_path = download_example_dataset(download_dir="dataset_examples")

dataset = ls.Dataset.create()
dataset.add_samples_from_yolo(
    data_yaml=f"{dataset_path}/road_signs_yolo/data.yaml",
)

ls.start_gui()
```

Run the script with `python example_yolo.py`. Now you can inspect samples with their assigned annotations in the app.

### COCO Instance Segmentation

To run an instance segmentation example using a [COCO](https://labelformat.com/formats/object-detection/coco/) dataset, create a file named
`example_coco.py`:

```python title="example_coco.py"
import lightly_studio as ls
from lightly_studio.utils import download_example_dataset

# Download the example dataset (will be skipped if it already exists)
dataset_path = download_example_dataset(download_dir="dataset_examples")

dataset = ls.Dataset.create()
dataset.add_samples_from_coco(
    annotations_json=f"{dataset_path}/coco_subset_128_images/instances_train2017.json",
    images_path=f"{dataset_path}/coco_subset_128_images/images",
    annotation_type=ls.AnnotationType.INSTANCE_SEGMENTATION,
)

ls.start_gui()
```

Run the script via `python example_coco.py`. Now you can inspect samples with their assigned annotations in the app.

### COCO Captions

To run a caption example using a COCO dataset, create a file named `example_coco_captions.py`:

```python title="example_coco_captions.py"
import lightly_studio as ls
from lightly_studio.utils import download_example_dataset

# Download the example dataset (will be skipped if it already exists)
dataset_path = download_example_dataset(download_dir="dataset_examples")

dataset = ls.Dataset.create()
dataset.add_samples_from_coco_caption(
    annotations_json=f"{dataset_path}/coco_subset_128_images/captions_train2017.json",
    images_path=f"{dataset_path}/coco_subset_128_images/images",
)

ls.start_gui()
```

Run the script with `python example_coco_captions.py`. Now you can inspect samples with their assigned captions in the app.

## 🐍 Python Interface

LightlyStudio has a powerful Python interface. You can not only index datasets but also query and manipulate them using code.

### ☁️ Using Cloud Storage
To load images directly from a cloud storage provider (like AWS S3, GCS, etc.), you must first install the required dependencies:

```py
pip install "lightly-studio[cloud-storage]"
```

This installs the necessary libraries: s3fs (for S3), gcsfs (for GCS), and adlfs (for Azure).
Our tool uses the fsspec library, which also supports other file systems. If you need a different provider (like FTP, SSH, etc.), you can find the required library in the [fsspec documentation](https://filesystem-spec.readthedocs.io/en/latest/api.html#other-known-implementations) and install it manually (e.g., pip install sftpfs).

**Current Support Limitations:**

* **Images:** Your images can be located in a cloud bucket (e.g., `s3://my-bucket/images/`)
* **Videos:** Your video files must currently be local. Cloud support is coming soon.
* **Annotations (Labels):** Your annotation files (like `labels.json` or a `labels/` directory) must be local on your machine. Loading annotations from cloud storage is not yet supported.

### Dataset

The dataset is the main entity of the python interface. It is used to setup the dataset,
start the GUI, run queries and perform selections. It holds the connection to the
database file.

```py
import lightly_studio as ls

# Different loading options:
dataset = ls.Dataset.create()

# You can load data also from cloud storage
dataset.add_images_from_path(path="s3://my-bucket/path/to/images/")

# And at any given time you can append more data (even across sources)
dataset.add_images_from_path(path="gcs://my-bucket-2/path/to/more-images/")
dataset.add_images_from_path(path="local-folder/some-data-not-in-the-cloud-yet")

# Load existing .db file
dataset = ls.Dataset.load()
```
#### Reusing a dataset and appending data

Datasets persist in a DuckDB file (`lightly_studio.db` by default). All tags, annotations, captions, metadata, and embeddings are saved, so you can stop and resume anytime. Use `Dataset.load_or_create` to reopen existing datasets:

```python
from __future__ import annotations

import lightly_studio as ls

dataset = ls.Dataset.load_or_create(name="my-dataset")

# Only new samples are added by `add_images_from_path`
for image_dir in IMAGE_DIRS:
    dataset.add_images_from_path(path=image_dir)

ls.start_gui()
```

**Notes:**
- The first time you run this script a new db is created and the data indexed
- If you add more images to the folder only the new data is indexed
- All annotations, tags, and metadata persist across sessions as long as the `lightly_studio.db` file in the working dir exists.

##### Custom database path

To use a different database file, initialize the database manager before creating datasets:

```python
import lightly_studio as ls

ls.db_manager.connect(db_file="lightly_studio.db")
dataset = ls.Dataset.load_or_create(name=DATASET_NAME)
```

### Sample

A sample is a single data instance, a dataset holds the reference to all samples. One can access samples individually and read or write on a samples attributes.

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
s.tags             # The set of sample tags (set[str]), e.g. {"tag1", "tag2"}
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

### Selection
LightlyStudio offers a premium feature to perform automated data selection. [Contact us](https://www.lightly.ai/contact) to get access to premium features. Selecting the right subset of your data can save labeling cost and training time while improving model quality. Selection in LightlyStudio automatically picks the most useful samples -  those that are both representative (typical) and diverse (novel).

You can mix and match these strategies to fit your goal: stable core data, edge cases, or fixing class imbalances.

```py
from lightly_studio.selection.selection_config import (
    MetadataWeightingStrategy,
    EmbeddingDiversityStrategy,
    AnnotationClassBalancingStrategy,
)

...

# Compute typicality and store it as `typicality` metadata
dataset.compute_typicality_metadata(metadata_name="typicality")

# Select 10 samples by combining typicality, diversity, and class balancing.
dataset.query().selection().multi_strategies(
    n_samples_to_select=10,
    selection_result_tag_name="multi_strategy_selection",
    selection_strategies=[
        MetadataWeightingStrategy(metadata_key="typicality", strength=1.0),
        EmbeddingDiversityStrategy(embedding_model_name="my_model_name", strength=2.0),
        AnnotationClassBalancingStrategy(target_distribution="uniform", strength=1.0),
    ],
)
```

## 🤝 Contribute

We welcome contributions! Please check our issues page for current tasks and improvements, or propose new issues yourself.

## 💬 Contact

[![Website](https://img.shields.io/badge/Website-lightly.ai-blue?style=for-the-badge&logo=safari&logoColor=white)](https://www.lightly.ai/lightly-studio) <br>
[![Discord](https://img.shields.io/discord/752876370337726585?style=for-the-badge&logo=discord&logoColor=white&label=discord&color=7289da)](https://discord.gg/xvNJW94) <br>
[![GitHub](https://img.shields.io/badge/GitHub-lightly--ai-black?style=for-the-badge&logo=github&logoColor=white)](https://github.com/lightly-ai/lightly-studio) <br>
[![X](https://img.shields.io/badge/X-lightlyai-black?style=for-the-badge&logo=x&logoColor=white)](https://x.com/lightlyai) <br>
[![YouTube](https://img.shields.io/badge/YouTube-lightly--tech-blue?style=for-the-badge&logo=YouTube&logoColor=white)](https://www.youtube.com/channel/UCAz60UdQ9Q3jPqqZi-6bmXw) <br>
[![LinkedIn](https://img.shields.io/badge/LinkedIn-lightly--tech-blue?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/company/lightly-tech)
