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

<p align="center">
  <img src="assets/readme/hero_showcase.gif" alt="LightlyStudio: an image grid with annotations next to an embedding plot, a cluster selection filtering the grid, and the annotation editor open on one image" width="100%" />
</p>

<p align="center">The embedding plot shows how images relate to each other, with a preview on hover. A lasso selection filters the grid to one cluster. A search for "coffee" finds a match, and the annotation editor opens to label it.</p>
<p align="center"><strong>⚡ Works smoothly with 2M+ images, embeddings included, on a single MacBook (M1, 16GB RAM).</strong></p>

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

LightlyStudio is a browser app that runs on your own computer. Load your data into the local
database with a Python script, then start the server and explore it in your browser.

<details open>
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

Other starting points:
[YOLO datasets](https://docs.lightly.ai/studio/dataset_setup/image_dataset/#from-an-annotation-format),
[video folders](https://docs.lightly.ai/studio/dataset_setup/video_dataset/),
[custom annotations](https://docs.lightly.ai/studio/concepts_and_tools/annotations/#annotations-in-python),
[model evaluation](https://docs.lightly.ai/studio/concepts_and_tools/evaluation/#model-evaluation-in-python),
and [notebooks](https://docs.lightly.ai/studio/dataset_setup/notebooks/).

Prefer a guided, end-to-end walkthrough? Follow the tutorial
[Curate a Traffic CCTV Dataset for YOLO Training](https://docs.lightly.ai/studio/tutorials/yolo-traffic-cctv-object-detection/) — from raw images to a trained model.
Or try LightlyStudio without installing anything: [open the example notebook in Colab](https://colab.research.google.com/github/lightly-ai/lightly-studio/blob/main/lightly_studio/src/lightly_studio/examples/example_notebook.ipynb).

## 📚 Tutorials

Step-by-step guides covering complete workflows — from raw, unlabeled data to a trained and evaluated model:

- **[Curate a Traffic CCTV Dataset for YOLO Training](https://docs.lightly.ai/studio/tutorials/yolo-traffic-cctv-object-detection/):** Explore embeddings, remove near-duplicates, auto-label with a detection plugin, and review annotations before training.
- **[Evaluate YOLO26 on Your Dataset with LightlyStudio](https://docs.lightly.ai/studio/tutorials/yolo26-model-evaluation/):** Compare predictions against ground truth, use the confusion matrix and embeddings to find failure patterns, and export issues for relabeling.

## 🐍 Python Interface

Everything in LightlyStudio is scriptable: index datasets, query and edit samples, sample
subsets, and export the result. Full documentation at
[docs.lightly.ai/studio](https://docs.lightly.ai/studio).

**Set up a dataset**

- [Image datasets](https://docs.lightly.ai/studio/dataset_setup/image_dataset/) — index folders, COCO, and YOLO data
- [Video datasets](https://docs.lightly.ai/studio/dataset_setup/video_dataset/) — index videos and work with frames
- [Cloud storage](https://docs.lightly.ai/studio/dataset_setup/cloud_storage/) — read from S3, GCS, or Azure
- [Reuse datasets](https://docs.lightly.ai/studio/dataset_setup/reuse_datasets/) — append to an existing database, or point at a custom path
- [Notebooks](https://docs.lightly.ai/studio/dataset_setup/notebooks/) — run the GUI inside Jupyter or Colab

**Work with your data**

- [Query, filter, and sort](https://docs.lightly.ai/studio/concepts_and_tools/search_and_filter/#query-in-python) — build reusable subsets in Python
- [Lightly Query Language](https://docs.lightly.ai/studio/concepts_and_tools/lightly_query_language/) — the query syntax shared by the GUI and Python
- [Annotations](https://docs.lightly.ai/studio/concepts_and_tools/annotations/), [Tags](https://docs.lightly.ai/studio/concepts_and_tools/tags/), [Metadata](https://docs.lightly.ai/studio/concepts_and_tools/metadata/), [Captions](https://docs.lightly.ai/studio/concepts_and_tools/captions/), [Embeddings](https://docs.lightly.ai/studio/concepts_and_tools/embeddings/)
- [Sampling](https://docs.lightly.ai/studio/concepts_and_tools/sampling/) — pick the most typical and diverse samples to cut labeling cost
- [Model evaluation](https://docs.lightly.ai/studio/concepts_and_tools/evaluation/) — compare predictions against ground truth
- [Plugins](https://docs.lightly.ai/studio/concepts_and_tools/plugins/) — auto-label with SAM and other models
- [Export](https://docs.lightly.ai/studio/concepts_and_tools/export/) — write a query back out as COCO or YOLO

**API reference**

[Dataset](https://docs.lightly.ai/studio/api/dataset/) ·
[Sample](https://docs.lightly.ai/studio/api/sample/) ·
[DatasetQuery](https://docs.lightly.ai/studio/api/dataset_query/) ·
[Sampling](https://docs.lightly.ai/studio/api/sampling/) ·
[Embeddings](https://docs.lightly.ai/studio/api/embeddings/) ·
[Annotation](https://docs.lightly.ai/studio/api/annotation/) ·
[Model Evaluation](https://docs.lightly.ai/studio/api/evaluation/) ·
[Plugin](https://docs.lightly.ai/studio/api/plugin/)

## 🤝 Contribute

We welcome contributions! Please check our issues page for current tasks and improvements, or propose new issues yourself.

## 💬 Contact

[![Website](https://img.shields.io/badge/Website-lightly.ai-blue?style=for-the-badge&logo=safari&logoColor=white)](https://www.lightly.ai/lightly-studio) <br>
[![Discord](https://img.shields.io/discord/752876370337726585?style=for-the-badge&logo=discord&logoColor=white&label=discord&color=7289da)](https://discord.gg/xvNJW94) <br>
[![GitHub](https://img.shields.io/badge/GitHub-lightly--ai-black?style=for-the-badge&logo=github&logoColor=white)](https://github.com/lightly-ai/lightly-studio) <br>
[![X](https://img.shields.io/badge/X-lightlyai-black?style=for-the-badge&logo=x&logoColor=white)](https://x.com/lightlyai) <br>
[![YouTube](https://img.shields.io/badge/YouTube-lightly--tech-blue?style=for-the-badge&logo=YouTube&logoColor=white)](https://www.youtube.com/channel/UCAz60UdQ9Q3jPqqZi-6bmXw) <br>
[![LinkedIn](https://img.shields.io/badge/LinkedIn-lightly--tech-blue?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/company/lightly-tech)
