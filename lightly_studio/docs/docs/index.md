# Welcome to LightlyStudio!

**[LightlyStudio](https://www.lightly.ai/lightly-studio)** is an open-source tool designed to unify
your data workflows from curation, annotation and management. Built with Rust for speed and
efficiency, it lets you work seamlessly with datasets like COCO and ImageNet, even on a MacBook Pro
with an M1 chip and 16 GB of memory.

=== "Explore"

    ![Image title](https://storage.googleapis.com/lightly-public/studio/search.gif){ width="100%"}
    _Discover insights instantly with AI-powered search and smart filters.
    Learn more in [Search and Filter](concepts_and_tools/search_and_filter.md)._

=== "Annotate"

    ![Image title](https://storage.googleapis.com/lightly-public/studio/annotate.gif){ width="100%" }
    _Create, edit, or remove annotations directly within your dataset._

=== "Embedding Plot"

    ![Image title](https://storage.googleapis.com/lightly-public/studio/embedding.gif){ width="100%" }
    _Visualize your dataset’s structure in the embedding space projected with [PaCMAP](https://github.com/YingfanWang/PaCMAP)._

=== "Export"

    ![Image title](https://storage.googleapis.com/lightly-public/studio/export.gif){ width="100%" }
    _Export selected samples and annotations in your preferred format._

## Installation

Ensure you have **Python 3.9 to 3.14**. We strongly recommend using a virtual environment.

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

    1. Create a file named `example_image.py` with the following contents:

        ```python title="example_image.py"
        import lightly_studio as ls

        # Download the example dataset (will be skipped if it already exists)
        dataset_path = ls.utils.download_example_dataset(download_dir="dataset_examples")

        # Indexes the dataset, creates embeddings and stores everything in the database.
        dataset = ls.ImageDataset.create()
        dataset.add_images_from_path(
            path=f"{dataset_path}/coco_subset_128_images/images",
        )

        # Start the UI server on port 8001. Use env variables to change port and host:
        # LIGHTLY_STUDIO_PORT=8002
        # LIGHTLY_STUDIO_HOST=0.0.0.0
        ls.start_gui()
        ```

    1. Run `python example_image.py` in your terminal.
    1. Click on the printed URL to open the app in your browser.

=== "Video Folder"

    1. Create a file named `example_video.py` with the following contents:

        ```python title="example_video.py"
        import lightly_studio as ls

        # Download the example dataset (will be skipped if it already exists)
        dataset_path = ls.utils.download_example_dataset(download_dir="dataset_examples")

        # Create a dataset and populate it with videos.
        dataset = ls.VideoDataset.create()
        dataset.add_videos_from_path(path=f"{dataset_path}/youtube_vis_50_videos/train/videos")

        # Start the UI server.
        ls.start_gui()
        ```

    1. Run `python example_video.py` in your terminal.
    1. Click on the printed URL to open the app in your browser.

=== "YOLO Object Detection"

    1. Create a file named `example_yolo.py` with the following contents:

        ```python title="example_yolo.py"
        import lightly_studio as ls

        # Download the example dataset (will be skipped if it already exists)
        dataset_path = ls.utils.download_example_dataset(download_dir="dataset_examples")

        dataset = ls.ImageDataset.create()
        dataset.add_samples_from_yolo(
            data_yaml=f"{dataset_path}/road_signs_yolo/data.yaml",
        )

        ls.start_gui()
        ```

    1. Run `python example_yolo.py` in your terminal.
    1. Click on the printed URL to open the app in your browser.

=== "COCO Instance Segmentation"

    1. Create a file named `example_coco.py` with the following contents:

        ```python title="example_coco.py"
        import lightly_studio as ls

        # Download the example dataset (will be skipped if it already exists)
        dataset_path = ls.utils.download_example_dataset(download_dir="dataset_examples")

        dataset = ls.ImageDataset.create()
        dataset.add_samples_from_coco(
            annotations_json=f"{dataset_path}/coco_subset_128_images/instances_train2017.json",
            images_path=f"{dataset_path}/coco_subset_128_images/images",
            annotation_type=ls.AnnotationType.INSTANCE_SEGMENTATION,
        )

        ls.start_gui()
        ```

    1. Run `python example_coco.py` in your terminal.
    1. Click on the printed URL to open the app in your browser.

**How It Works**

-  Your **Python script** creates a LightlyStudio **dataset**.
-  The `dataset.add_<samples>_from_<source>` functions read your samples and annotations, calculate
   embeddings, and save metadata to a local `lightly_studio.db` file (using DuckDB).
-  `ls.start_gui()` starts a **local backend API** server.
-  This server reads from `lightly_studio.db` and serves data to the **UI Application** running in
   your browser (by default `http://localhost:8001`).
-  Images and videos are streamed from their original local folder or remote storage for display in the UI.

!!! note "For Linux Users"
    We recommend using Firefox for the best experience with embedding plots, as other browsers might
    not render them correctly.

## Feature Overview

### Datasets

<div class="grid cards small" markdown>

-   **[Image Dataset](dataset_setup/image_dataset.md)**

    [![Image Dataset](https://storage.googleapis.com/lightly-public/studio/docs_cards/image_dataset.png)](dataset_setup/image_dataset.md)

-   **[Video Dataset](dataset_setup/video_dataset.md)**

    [![Video Dataset](https://storage.googleapis.com/lightly-public/studio/docs_cards/video_dataset.png)](dataset_setup/video_dataset.md)

</div>

### Concepts

<div class="grid cards small" markdown>

-   **[Annotations](concepts_and_tools/annotations.md)**

    [![Annotations](https://storage.googleapis.com/lightly-public/studio/docs_cards/annotation.png)](concepts_and_tools/annotations.md)

-   **[Tags](concepts_and_tools/tags.md)**

    [![Tags](https://storage.googleapis.com/lightly-public/studio/docs_cards/tags.png)](concepts_and_tools/tags.md)

-   **[Captions](concepts_and_tools/captions.md)**

    [![Captions](https://storage.googleapis.com/lightly-public/studio/docs_cards/captions.png)](concepts_and_tools/captions.md)

-   **[Metadata](concepts_and_tools/metadata.md)**

    [![Metadata](https://storage.googleapis.com/lightly-public/studio/docs_cards/metadata.png)](concepts_and_tools/metadata.md)

-   **[Embeddings](concepts_and_tools/embeddings.md)**

    [![Embeddings](https://storage.googleapis.com/lightly-public/studio/docs_cards/embeddings.png)](concepts_and_tools/embeddings.md)

</div>

### Tools

<div class="grid cards small" markdown>

-   **[Search and Filter](concepts_and_tools/search_and_filter.md)**

    [![Search and Filter](https://storage.googleapis.com/lightly-public/studio/docs_cards/search_and_filter.png)](concepts_and_tools/search_and_filter.md)

-   **[Export](concepts_and_tools/export.md)**

    [![Export](https://storage.googleapis.com/lightly-public/studio/docs_cards/export.png)](concepts_and_tools/export.md)

-   **[Sampling](concepts_and_tools/sampling.md)**

    [![Sampling](https://storage.googleapis.com/lightly-public/studio/docs_cards/sampling.png)](concepts_and_tools/sampling.md)

-   **[Plugins](concepts_and_tools/plugins.md)**

    [![Plugins](https://storage.googleapis.com/lightly-public/studio/docs_cards/plugins.png)](concepts_and_tools/plugins.md)

</div>

## Python API

LightlyStudio has a powerful [Python interface](api/index.md). You can not only index datasets but
also query and manipulate them using code. It supports local and cloud-hosted image and video
folders; see [Using Cloud Storage](api/index.md#using-cloud-storage) for setup and limitations.
