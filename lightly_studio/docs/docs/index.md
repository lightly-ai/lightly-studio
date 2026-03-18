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
    from lightly_studio.utils import download_example_dataset

    # Download the example dataset (will be skipped if it already exists)
    dataset_path = download_example_dataset(download_dir="dataset_examples")

    # Create a dataset and populate it with videos.
    dataset = ls.VideoDataset.create()
    dataset.add_videos_from_path(path=f"{dataset_path}/youtube_vis_50_videos/train/videos")

    # Start the UI server.
    ls.start_gui()
    ```

    Run the script with `python example_video.py`. Now you can inspect videos in the app.

    The same `dataset.add_videos_from_path()` call also accepts cloud storage URLs such as `s3://my-bucket/videos/` after installing `pip install "lightly-studio[cloud-storage]"`.


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
5.  Images and videos are streamed from their original local folder or remote storage for display in the UI.

!!! note "For Linux Users"
    We recommend using Firefox for the best experience with embedding plots, as other browsers might not render them correctly.

## Python API

LightlyStudio has a powerful [Python interface](api/index.md). You can not only index datasets but also query and manipulate them using code. It supports local and cloud-hosted image and video folders; see [Using Cloud Storage](api/index.md#using-cloud-storage) for setup and limitations.

## Plugins

LightlyStudio offers the possibility to extend its functionality by using [plugins](concepts_and_tools/plugins.md). Users can define their own plugins or use pre-defined ones.
