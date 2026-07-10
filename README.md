<p align="center">
  <a href="https://lightly.ai/lightly-studio"> 
    <picture>
      <source
        media="(prefers-color-scheme: dark)"
        srcset="https://storage.googleapis.com/lightly-public/studio/lightlystudio_standard_horizontal_light.png"
      />
      <source
        media="(prefers-color-scheme: light)"
        srcset="https://storage.googleapis.com/lightly-public/studio/lightlystudio_standard_horizontal_dark.png"
      />
      <img
        src="https://storage.googleapis.com/lightly-public/studio/lightlystudio_standard_horizontal_dark.png"
        height="50"
        alt="LightlyStudio logo"
      />
    </picture>
  </a>
</p>
<p align="center"><strong>Curate, Annotate, and Manage Your Data in LightlyStudio.</strong></p>
<p align="center">
  <a href="https://pypi.org/project/lightly-studio"><img src="https://img.shields.io/pypi/pyversions/lightly-studio" alt="PyPI python" /></a>
  <a href="https://pypi.org/project/lightly-studio"><img src="https://badge.fury.io/py/lightly-studio.svg" alt="PyPI version" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-Apache%202.0-blue.svg" alt="License" /></a>
  <a href="https://docs.lightly.ai/studio"><img src="https://img.shields.io/badge/Docs-blue" alt="Docs" /></a>
  <a href="https://colab.research.google.com/github/lightly-ai/lightly-studio/blob/main/lightly_studio/src/lightly_studio/examples/example_notebook.ipynb"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab" /></a>
</p>

---

# Welcome to LightlyStudio!

We at Lightly created **LightlyStudio**, an open-source tool designed to unify your data workflows from curation, annotation, model evaluation and management in a single tool. Since we're big fans of Rust we used it to speed things up. You can work with COCO and ImageNet on a Macbook Pro with M1 and 16GB of memory!

<p align="center">
  <video
    src="https://github.com/user-attachments/assets/012974ce-1040-40f9-9f7e-41a45c56bf1c"
    width="70%"
    controls
    loop
    muted
  ></video>
  <br>
</p>

## 💻 Installation

Runs on **Python 3.9 to 3.14** on Windows, Linux and MacOS. We recommend **Python 3.10** for the best compatibility with plugins such as SAM autolabeling.

```shell
pip install lightly-studio
```


## Workflows

<table>
  <tr>
    <td align="center">
      <a href="https://docs.lightly.ai/studio/dataset_setup/image_dataset/">
        <img src="https://storage.googleapis.com/lightly-public/studio/docs_cards/image_dataset.png" width="400" alt="Image Datasets"/>
      </a>
      <br/><strong>Image Dataset</strong>
    </td>
    <td align="center">
      <a href="https://docs.lightly.ai/studio/dataset_setup/video_dataset/">
        <img src="https://storage.googleapis.com/lightly-public/studio/docs_cards/video_dataset.png" width="400" alt="Video Dataset"/>
      </a>
      <br/><strong>Video Dataset</strong>
    </td>
    <td align="center">
      <a href="https://docs.lightly.ai/studio/concepts_and_tools/annotations/">
        <img src="https://storage.googleapis.com/lightly-public/studio/docs_cards/annotation.png" width="400" alt="Annotate"/>
      </a>
      <br/><strong>Annotation</strong>
    </td>
  </tr>
  <tr>
    <td align="center">
      <a href="https://docs.lightly.ai/studio/concepts_and_tools/sampling/">
        <img src="https://storage.googleapis.com/lightly-public/studio/docs_cards/sampling.png" width="400" alt="Curate"/>
      </a>
      <br/><strong>Curation</strong>
    </td>
    <td align="center">
      <a href="https://docs.lightly.ai/studio/concepts_and_tools/plugins/">
        <img src="https://storage.googleapis.com/lightly-public/studio/docs_cards/plugins.png" width="400" alt="Plugins"/>
      </a>
      <br/><strong>Plugins</strong>
    </td>
    <td align="center">
      <a href="https://docs.lightly.ai/studio/concepts_and_tools/evaluation/">
        <img src="https://storage.googleapis.com/lightly-public/studio/docs_cards/model_evaluation.png" width="400" alt="Model Evaluation"/>
      </a>
      <br/><strong>Model Evaluation</strong>
    </td>
  </tr>
</table>


## 🚀 Quickstart

LightlyStudio is a browser app that runs on your own computer. Use it in two simple steps:

1. Load your data into the local database with a Python script.
2. Start the server and explore the data in your browser.

Prefer a guided, end-to-end walkthrough? Follow the tutorial
[Curate a Traffic CCTV Dataset for YOLO Training](https://docs.lightly.ai/studio/tutorials/yolo-traffic-cctv-object-detection/) — from raw images to a trained model.
Or try LightlyStudio without installing anything: [open the example notebook in Colab](https://colab.research.google.com/github/lightly-ai/lightly-studio/blob/main/lightly_studio/src/lightly_studio/examples/example_notebook.ipynb).

Get started with one of these example workflows:

<details open>
<summary><strong>Evaluate object detection predictions on a COCO dataset</strong></summary>

Create a file named `example_coco_od_evaluation.py`:

```python
import lightly_studio as ls
from lightly_studio.core.dataset_query.image_sample_field import ImageSampleField
from lightly_studio.evaluation.image_dataset_evaluate import ObjectDetectionEvaluationConfig


# Download the example dataset (will be skipped if it already exists)
dataset_path = ls.utils.download_example_dataset(download_dir="dataset_examples")

images_path = f"{dataset_path}/coco_subset_128_images/images"
evaluation_config = ObjectDetectionEvaluationConfig(
    iou_threshold=0.5,
    classwise=True,
)

dataset = ls.ImageDataset.load_or_create()
dataset.add_images_from_path(path=images_path)
# Add ground truth annotations
dataset.add_annotations_from_coco(
    annotations_json=f"{dataset_path}/coco_subset_128_images/instances_train2017.json",
    images_root=images_path,
    annotation_source="ground_truth",
)
# Add predictions annotations
dataset.add_annotations_from_coco(
    annotations_json=f"{dataset_path}/coco_subset_128_images/predictions_train2017.json",
    images_root=images_path,
    annotation_source="predictions",
)
# Optional: tag a subset of samples to run the evaluation on.
dataset.query()[:10].add_tag("evaluated_samples")
# Create query for tagged samples
tagged_evaluation_query = dataset.query().match(ImageSampleField.tags.contains("evaluated_samples"))

dataset.evaluate(query=tagged_evaluation_query).object_detection(
    name="od_evaluation",
    gt_annotation_source="ground_truth",
    pred_annotation_source="predictions",
    config=evaluation_config,
)

ls.start_gui()
```
</details>

<details>
<summary><strong>Index a COCO dataset</strong></summary>

Create a file named `example_coco.py`:

```python
import lightly_studio as ls

# Download the example dataset (will be skipped if it already exists)
dataset_path = ls.utils.download_example_dataset(download_dir="dataset_examples")

dataset = ls.ImageDataset.load_or_create()
dataset.add_samples_from_coco(
    annotations_json=f"{dataset_path}/coco_subset_128_images/instances_train2017.json",
    images_path=f"{dataset_path}/coco_subset_128_images/images",
)
# Optional: tag a subset of samples to filter them in the GUI. 
dataset.query()[:10].add_tag("sample_subset")

ls.start_gui()
```

Run `python example_coco.py` and open the printed URL to inspect images with their annotations.

To import COCO segmentation masks instead of object detections, set:

```python
annotation_type=ls.AnnotationType.SEGMENTATION_MASK
```

</details>

<details>
<summary><strong>Index a YOLO dataset</strong></summary>

Create a file named `example_yolo.py`:

```python
import lightly_studio as ls

# Download the example dataset (will be skipped if it already exists)
dataset_path = ls.utils.download_example_dataset(download_dir="dataset_examples")

dataset = ls.ImageDataset.load_or_create()
dataset.add_samples_from_yolo(
    data_yaml=f"{dataset_path}/road_signs_yolo/data.yaml",
)

ls.start_gui()
```

Run `python example_yolo.py` and open the printed URL to inspect images with their annotations.

</details>

<details>
<summary><strong>Add custom annotations</strong></summary>

Create a file named `example_custom_annotations.py`:

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
dataset = ls.ImageDataset.load_or_create()
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

Run `python example_custom_annotations.py` and open the printed URL to inspect the
classification, bounding box, and segmentation mask.

</details>

<details>
<summary><strong>Working with notebooks</strong></summary>

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/lightly-ai/lightly-studio/blob/main/lightly_studio/src/lightly_studio/examples/example_notebook.ipynb)

```python
import lightly_studio as ls

dataset_path = ls.utils.download_example_dataset(download_dir="dataset_examples")
dataset = ls.ImageDataset.load_or_create()
dataset.add_images_from_path(path=f"{dataset_path}/coco_subset_128_images/images")

# Colab needs 0.0.0.0 to expose the port.
server = ls.start_gui_background(host="0.0.0.0")
```

Jupyter:

```python
from IPython.display import IFrame, display

display(IFrame(server.url, width=1000, height=800))
```

Colab:

```python
from google.colab import output

output.serve_kernel_port_as_iframe(server.port, width=1000, height=800)
```
</details>

<details>
<summary><strong>Index a folder of images for curation and labeling</strong></summary>

Create a file named `example_image.py`:

```python
import lightly_studio as ls

# Download the example dataset (will be skipped if it already exists)
dataset_path = ls.utils.download_example_dataset(download_dir="dataset_examples")

# Index the images, create embeddings, and store everything in the local database.
dataset = ls.ImageDataset.load_or_create()
dataset.add_images_from_path(
    path=f"{dataset_path}/coco_subset_128_images/images",
)

# Start the UI server on localhost:8001.
# Pass `host` and `port` parameters to customize it.
ls.start_gui()
```

Run `python example_image.py` and open the printed URL in your browser.

</details>

<details>
<summary><strong>Index a folder of videos for curation and labeling</strong></summary>

```python
import lightly_studio as ls

dataset_path = ls.utils.download_example_dataset(download_dir="dataset_examples")

dataset = ls.VideoDataset.load_or_create()
dataset.add_videos_from_path(path=f"{dataset_path}/youtube_vis_50_videos/train/videos")

ls.start_gui()
```


</details>

## 📚 Tutorials

Step-by-step guides covering complete workflows — from raw, unlabeled data to a trained and evaluated model:

- **[Curate a Traffic CCTV Dataset for YOLO Training](https://docs.lightly.ai/studio/tutorials/yolo-traffic-cctv-object-detection/):** Explore embeddings, remove near-duplicates, auto-label with a detection plugin, and review annotations before training.
- **[Evaluate YOLO26 on Your Dataset with LightlyStudio](https://docs.lightly.ai/studio/tutorials/yolo26-model-evaluation/):** Compare predictions against ground truth, use the confusion matrix and embeddings to find failure patterns, and export issues for relabeling.

## 🐍 Python Interface

LightlyStudio has a powerful Python interface. You can not only index datasets but also query and manipulate them using code.

### ☁️ Using Cloud Storage
To load images or videos directly from a cloud storage provider (like AWS S3, GCS, etc.), you must first install the required dependencies:

```shell
pip install "lightly-studio[cloud-storage]"
```

This installs the necessary libraries: s3fs (for S3), gcsfs (for GCS), and adlfs (for Azure).
Our tool uses the fsspec library, which also supports other file systems. If you need a different provider (like FTP, SSH, etc.), you can find the required library in the [fsspec documentation](https://filesystem-spec.readthedocs.io/en/latest/api.html#other-known-implementations) and install it manually (e.g., pip install sftpfs).

**Current Support Limitations for Annotations:** Cloud-hosted annotations are currently supported for COCO object detection and segmentation mask; other dataset importers still expect local files.

### Dataset

The dataset is the main entity of the python interface. It is used to setup the dataset,
start the GUI, run queries and perform sampling. It holds the connection to the
database file.

```py
import lightly_studio as ls

# Different loading options:
dataset = ls.ImageDataset.create()

# You can load data also from cloud storage
dataset.add_images_from_path(path="s3://my-bucket/path/to/images/")

# And at any given time you can append more data (even across sources)
dataset.add_images_from_path(path="gcs://my-bucket-2/path/to/more-images/")
dataset.add_images_from_path(path="local-folder/some-data-not-in-the-cloud-yet")

# Load existing .db file
dataset = ls.ImageDataset.load()
```
#### Reusing a dataset and appending data

Datasets persist in a DuckDB file (`lightly_studio.db` by default). All tags, annotations, captions, metadata, and embeddings are saved, so you can stop and resume anytime. Use `Dataset.load_or_create` to reopen existing datasets:

```python
import lightly_studio as ls

dataset = ls.ImageDataset.load_or_create(name="my-dataset")

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
dataset = ls.ImageDataset.load_or_create(name=DATASET_NAME)
```

### Sample

A sample is a single data instance, a dataset holds the reference to all samples. One can access samples individually and read or write on a samples attributes.

```py
from lightly_studio.core.annotation.object_detection import ObjectDetectionAnnotation

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

# Access annotations
for annotation in sample.annotations:
    if isinstance(annotation, ObjectDetectionAnnotation):
        print(annotation.x, annotation.y, annotation.width, annotation.height)
...
```

### Dataset Query

Dataset queries are a combination of filtering, sorting and slicing operations. For this the **Expressions** are used.

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

### Sampling
Sampling the right subset of your data can save labeling cost and training time while improving model quality. Sampling in LightlyStudio automatically picks the most useful samples - those that are both representative (typical) and diverse (novel).

You can mix and match these strategies to fit your goal: stable core data, edge cases, or fixing class imbalances.

```py
from lightly_studio.sampling.sampling_config import (
    MetadataWeightingStrategy,
    EmbeddingDiversityStrategy,
    AnnotationClassBalancingStrategy,
)

...

# Compute typicality and store it as `typicality` metadata
dataset.compute_typicality_metadata(metadata_name="typicality")

# Select 10 samples by combining typicality, diversity, and class balancing.
dataset.query().sampling().multi_strategies(
    n_samples_to_select=10,
    sampling_result_tag_name="multi_strategy_sampling",
    sampling_strategies=[
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
