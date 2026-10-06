# Welcome to LightlyStudio!

One integrated computer vision platform for labeling, curation, QA, and dataset management. Open-source at its core, [LightlyStudio](https://www.lightly.ai/lightly-studio) is built for ML engineers and organizations scaling computer vision.

<div class="grid cards" markdown>

-   **[LightlyStudio Enterprise](enterprise/index.md)**

    Working in a team and looking for collaboration features, role-based access permissions, and
    centrally managed cloud credentials?

    [Try LightlyStudio Enterprise →](https://studio.auth.lightly.ai/sign-up){ .md-button .md-button--primary }
    [Book a Demo →](https://www.lightly.ai/demo){ .md-button }
    { .ls-cta }

</div>

<p align="center">
  <video src="_static/hero_showcase.mp4" width="100%" autoplay loop muted playsinline></video>
</p>

<p align="center">The embedding plot shows how images relate to each other, with a preview on hover. A lasso selection filters the grid to one cluster. A search for "coffee" finds a match, and the annotation editor opens to label it.</p>
<p align="center"><strong>⚡ Works smoothly with 2M+ images, embeddings included, on a single MacBook (M1, 16GB RAM).</strong></p>

```shell
pip install lightly-studio
```

!!! success "Try it in 60 seconds"

    Want to try LightlyStudio instantly? Run:

    ```shell
    lightly-studio quickstart
    ```

    This downloads the COCO example dataset, loads it, and opens the GUI in your browser.

## Overview

<div class="grid cards small" markdown>

-   **[Data Ingest](workflows/image_dataset.md)**

    [![Image Dataset](https://storage.googleapis.com/lightly-public/studio/docs_cards/image_dataset.png)](workflows/image_dataset.md)

-   **[Data Management](workflows/tags.md)**

    [![Data Management](https://storage.googleapis.com/lightly-public/studio/docs_cards/tags.png)](workflows/tags.md)

-   **[Curate](workflows/search_and_filter.md)**

    [![Curate](https://storage.googleapis.com/lightly-public/studio/docs_cards/embeddings.png)](workflows/search_and_filter.md)

-   **[Annotate](workflows/annotations.md)**

    [![Annotate](https://storage.googleapis.com/lightly-public/studio/docs_cards/annotation.png)](workflows/annotations.md)

-   **[Evaluate](workflows/evaluation.md)**

    [![Evaluate](https://storage.googleapis.com/lightly-public/studio/docs_cards/model_evaluation.png)](workflows/evaluation.md)

-   **[Export and Train](workflows/export.md)**

    [![Export and Train](https://storage.googleapis.com/lightly-public/studio/docs_cards/export.png)](workflows/export.md)

-   **[Plugins](ecosystem/plugins.md)**

    [![Plugins](https://storage.googleapis.com/lightly-public/studio/docs_cards/plugins.png)](ecosystem/plugins.md)


</div>

## Quickstart

LightlyStudio works on Windows, Linux, and macOS with **Python 3.9 to 3.14**. We recommend
**Python 3.10** for the best compatibility with plugins such as SAM autolabeling.

??? tip "Recommended: install into a virtual environment"
    A virtual environment keeps LightlyStudio and its dependencies separate from other
    Python projects on your machine:

    === "Linux/macOS"

        ```shell
        python3 -m venv venv
        source venv/bin/activate
        pip install lightly-studio
        ```

    === "Windows"

        ```powershell
        python -m venv venv
        .\venv\Scripts\activate
        pip install lightly-studio
        ```

The examples below use the same example dataset by default, downloaded on the first run. Point
them at your own image, video, or YOLO/COCO dataset by changing the input path.

=== "COCO Object Detection"

    1. Create a file named `example_coco.py` with the following contents:

        ```python title="example_coco.py"
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

    1. Run `python example_coco.py` in your terminal.
    1. Click on the printed URL to open the app in your browser.

=== "YOLO Object Detection"

    1. Create a file named `example_yolo.py` with the following contents:

        ```python title="example_yolo.py"
        import lightly_studio as ls

        # Download the example dataset (will be skipped if it already exists)
        dataset_path = ls.utils.download_example_dataset(download_dir="dataset_examples")

        dataset = ls.ImageDataset.load_or_create()
        dataset.add_samples_from_yolo(
            data_yaml=f"{dataset_path}/road_signs_yolo/data.yaml",
        )

        ls.start_gui()
        ```

    1. Run `python example_yolo.py` in your terminal.
    1. Click on the printed URL to open the app in your browser.

=== "Raw Images"

    *Add images that have no annotations. LightlyStudio indexes and embeds them.*

    1. Create a file named `example_image.py` with the following contents:

        ```python title="example_image.py"
        import lightly_studio as ls

        # Download the example dataset (will be skipped if it already exists)
        dataset_path = ls.utils.download_example_dataset(download_dir="dataset_examples")

        # Indexes the dataset, creates embeddings and stores everything in the database.
        dataset = ls.ImageDataset.load_or_create()
        dataset.add_images_from_path(
            path=f"{dataset_path}/coco_subset_128_images/images",
        )

        # Start the UI server on localhost port 8001.
        # Pass `host` and `port` parameters to customize.
        ls.start_gui()
        ```

    1. Run `python example_image.py` in your terminal.
    1. Click on the printed URL to open the app in your browser.

=== "Raw Videos"

    *Add videos that have no annotations. LightlyStudio indexes and embeds them.*

    1. Create a file named `example_video.py` with the following contents:

        ```python title="example_video.py"
        import lightly_studio as ls

        # Download the example dataset (will be skipped if it already exists)
        dataset_path = ls.utils.download_example_dataset(download_dir="dataset_examples")

        # Create a dataset and populate it with videos.
        dataset = ls.VideoDataset.load_or_create()
        dataset.add_videos_from_path(path=f"{dataset_path}/youtube_vis_50_videos/train/videos")

        # Start the UI server.
        ls.start_gui()
        ```

    1. Run `python example_video.py` in your terminal.
    1. Click on the printed URL to open the app in your browser.

!!! tip
    Call `lightly-studio gui` instead of `ls.start_gui()` in Python to skip reindexing
    an already-loaded dataset.

Ready for a complete, end-to-end workflow? Follow the tutorial
[Curate a Traffic CCTV Dataset for YOLO Training](tutorials/yolo-traffic-cctv-object-detection.md)
to explore embeddings, remove near-duplicates, auto-label, and train a model — or browse
[all tutorials](tutorials/index.md).

## How It Works

-  Your **Python script** creates a LightlyStudio **dataset**.
-  The `dataset.add_<samples>_from_<source>` functions read your samples and annotations, calculate
   embeddings, and save metadata to a local `lightly_studio.db` file (using DuckDB).
-  `ls.start_gui()` starts a **local backend API** server.
-  This server reads from `lightly_studio.db` and serves data to the **UI Application** running in
   your browser (by default `http://localhost:8001`).
-  Images and videos are streamed from their original local folder or remote storage for display in the UI.

## Python API

LightlyStudio has a powerful [Python interface](api/dataset.md). You can not only index datasets but
also query and manipulate them using code. It supports local and cloud-hosted image and video
folders; see [Using Cloud Storage](ecosystem/cloud_storage.md) for setup and limitations.
