# Prepare a YOLO Traffic CCTV Dataset

!!! note "Draft tutorial placeholder"
    This tutorial page is a placeholder for the first LightlyStudio tutorial. Media assets and final editorial polish will be added in a later pass.

In this tutorial, we prepare a YOLO dataset for detecting objects in traffic CCTV images. We start from the `justjuu/traffic-accident-cctv-object-detection` dataset on Hugging Face, which contains CCTV images for traffic safety and surveillance use cases.

For this tutorial, we use only the images and treat them as an unannotated dataset. We do not use the existing annotations from the dataset. This lets us follow a realistic workflow where you start with a folder of raw images and need to prepare it for object detection model training.

We will use LightlyStudio to explore the data, curate useful samples, create and review object labels, export the final dataset in YOLO format, and run a short YOLO training job to verify the export.

!!! todo "Media placeholder"
    Add introductory media for the tutorial.

## Prerequisites

To follow this tutorial, make sure you have:

- Python 3.10 or newer.

## Installation

### Install LightlyStudio

To install LightlyStudio you can run the following Python pip command:

```bash
pip install "git+https://github.com/lightly-ai/lightly-studio-plugins.git#subdirectory=plugins/yolo_object_detection/"
```

### Install the YOLO Inference Plugin

There are two ways to bring model predictions into LightlyStudio for pre-labeling or auto-labeling.

- Add YOLO predictions directly in the Python script used to load the dataset.
- Use a plugin to run the model directly from the LightlyStudio GUI.

In this tutorial, we use the YOLO inference plugin. Install the plugin before starting the LightlyStudio GUI.

Run:

```bash
pip install "git+https://github.com/lightly-ai/lightly-studio-plugins.git#subdirectory=plugins/yolo_object_detection/"
```

!!! tip
    You need to install the plugin before running the GUI. If LightlyStudio is already running, stop the server, install the plugin, and then restart the server.

## Load the dataset

Create a Python script and define the path to your local image folder. Then, create a LightlyStudio dataset and load the images.

The `load_dataset.py` script below indexes the images and computes embeddings. This enables the embedding plot and semantic search in the LightlyStudio UI.

```python title="load_dataset.py"
import lightly_studio as ls
from lightly_studio.plugins.operator_registry import operator_registry
from lightly_plugins_yolo_object_detection.operator import YoloObjectDetectionOperator

# This is only needed if you want to download and use the example dataset
dataset_path = ls.utils.download_example_dataset(download_dir="dataset_examples")

dataset = ls.ImageDataset.create()

# Make sure the path is pointing to the correct folder
dataset.add_images_from_path(
    path=f"{dataset_path}/traffic-accident-cctv/train"
)

# In order to use plugins we need to register them
operator_registry.register(YoloObjectDetectionOperator())

# This will start the GUI and block the script from existing
ls.start_gui()
```

Run the script from your terminal:

```bash
python load_dataset.py
```

After the script starts, LightlyStudio prints the local URL where the GUI is available. You should see output similar to this:

```bash
INFO: Found 128 images in /path/to/your/image/folder.
INFO: Open the LightlyStudio GUI under: http://localhost:8001
INFO: Discovered plugin 'yolo_object_detection'
INFO: Operator 'YOLO Object Detection' started.
INFO: Uvicorn running on http://localhost:8001
INFO: Using MobileCLIP embedding generator for images.
```

Open the displayed URL (`http://localhost:8001`) in your browser to start exploring the dataset in LightlyStudio.

## Explore the dataset

Open the dataset in LightlyStudio and inspect the embedding plot by clicking on the Embed button on the upper right side of the GUI.

The embedding plot groups visually similar images close to each other. Use it to understand the dataset structure and identify samples that are useful for training, such as images containing vehicles, traffic scenes, accidents, or other relevant objects.

While exploring the dataset, you may notice that only a few samples are clear outliers. These outliers can include images without vehicles, blurry images, or samples that are not relevant to the task.

Let's tag these outliers so we can easily exclude them or review them later. For that, click on the lasso tool at the bottom of the embedding plot. Once selected you can draw a lasso around the embedding points of interest.

Next, select promising clusters in the embedding plot and inspect the corresponding images. When you find samples that are suitable for training, tag them so they can be exported or reviewed later as part of your training subset.

!!! todo "Media placeholder"
    Add `Screenshot 2026-06-25 at 09.26.40.png`.

## Refine the selection with a deduplication sampling

This dataset contains several visually similar images. Removing near-duplicates can help reduce redundancy in the training set and improve the quality of the YOLO model.

After tagging relevant examples in the previous step, use deduplication sampling to identify duplicate or near-duplicate images based on their embedding distance.

First, filter the dataset by the tag you created earlier, for example `vehicles`. Then open **Menu > Sampling** and run deduplication sampling.

!!! todo "Media placeholder"
    Add `Screen Recording 2026-06-25 at 09.34.50.gif`.

## Using Query Filter to tag suitable samples

After identifying outliers and duplicate samples, use the Query Filter to quickly select the remaining images and tag them as valid samples.

Open the query editor on the right side of the LightlyStudio and enter a query that excludes the tags you created in the previous steps. For example:

```text
NOT "empty" IN tags AND NOT "duplicate" IN tags
```

Update the tag names in the query to match the tags you used during data curation. For example, replace `"empty"` or `"duplicate"` with your own tag names if they are different.

!!! todo "Media placeholder"
    Add `create_valid_samples.gif`.

Click **Apply** to filter the dataset. Then press **CMD + A** on macOS or **CTRL + A** on Windows/Linux to select all visible samples, and create a new tag for them, such as `valid samples`.

This tag represents the curated set of valid, non-duplicate samples. You can use these samples later to create your training and test sets.

## Using the YOLO Plugin

Once you have finished curating the dataset, select the images you want to process or apply filters to define the active view. Then open the operator menu and choose the YOLO object detection plugin.

The plugin runs on the selected samples or on the images in the active view, depending on how it is launched. After the plugin finishes, review the generated annotations and adjust them if needed before exporting the training data.

!!! todo "Media placeholder"
    Add `Screen Recording 2026-06-25 at 10.09.09.gif`.

### Review and correct annotations

Some samples may not be annotated accurately, especially when the image quality is low, the objects are small, or the scene is difficult to interpret.

Review the generated annotations manually and check whether the bounding boxes and labels are correct. If needed, adjust the annotations by fixing incorrect boxes, adding missing objects, removing false detections, or correcting class labels.

!!! todo "Media placeholder"
    Add `improve_annotation.gif`.

Improving the annotation quality helps create a more reliable training dataset and can improve the performance of the final YOLO model.

You can also use the left filter panel to filter images by annotation class. This makes it easier to inspect groups of images with the same label and identify possible labeling mistakes, such as vehicles assigned to the wrong class or objects that should have been labeled differently.

!!! todo "Media placeholder"
    Add `Screenshot 2026-06-25 at 10.51.03.png`.

## Split the dataset into training and test sets

LightlyStudio provides smart sampling tools that can help you create a diverse training set.

First, use the left filter panel to select the valid samples you tagged in the previous step. Then open the sampling dialog again and choose diversity sampling.

Configure the sampling step to select 80% of the valid samples and assign them a new tag, such as `train`.

!!! todo "Media placeholder"
    Add `diversity.gif`.

After creating the training split, use the Query Filter to select the remaining valid samples that were not tagged as training samples. For example:

```bash
"valid samples" IN tags AND NOT "train" IN tags
```

Update the tag names in the query to match the tags you created in your project. Click **Apply**, select all visible samples with **CMD + A** on macOS or **CTRL + A** on Windows/Linux, and create a new tag, such as `test`.

## Export in YOLO format

To train and evaluate the YOLO model, export the curated `train` and `test` splits from LightlyStudio.

LightlyStudio supports exporting annotations through the GUI or the Python API. In this example, we use the Python export API to export the samples tagged as `train` and `test`.

```python
import lightly_studio as ls
from lightly_studio.core.dataset_query.image_sample_field import ImageSampleField

dataset = ls.ImageDataset.load(name="cctv_1")

# Tags to export
tags_to_export = ["train", "test"]

for tag in tags_to_export:
    query = dataset.query().match(ImageSampleField.tags.contains(tag))
    dataset.export(query).to_yolo_object_detections(f"{tag}_yolo/")
    print(f"Exported samples with tag '{tag}' to {tag}_yolo/")
```

After executing this script, you should see a similar output:

```text
Exported samples with tag 'train' to train_yolo/
Exported samples with tag 'test' to test_yolo/
```

You can use these exported directories to train and evaluate your YOLO object detection model.

## Evaluate the YOLO model

After exporting the dataset, run a short YOLO training and evaluation job to verify that the exported files can be used by a training pipeline.

The `train_yolo` directory contains the samples used for training, and the `test_yolo` directory contains the samples used for evaluation.

First, install Ultralytics if it is not already installed:

```bash
pip install ultralytics
```

Then create a Python script, for example `train_yolo.py`.

In this example, the images are stored in the original dataset folder, while the YOLO labels are split into `train_yolo` and `test_yolo`. The script creates symbolic links to the corresponding images inside each split, builds a combined `data.yaml` file, trains a YOLO model, and evaluates it on the test split.

```python title="train_yolo.py"
from pathlib import Path
from ultralytics import YOLO
import yaml
import lightly_studio as ls

dataset_path = ls.utils.download_example_dataset(download_dir="dataset_examples")

images_dir = Path(f"{dataset_path}/traffic-accident-cctv/train/")
train_yolo_dir = Path("train_yolo")
test_yolo_dir = Path("test_yolo")

def find_image(stem):
    candidate = images_dir / f"{stem}.jpg"
    if candidate.exists():
        return candidate
    return None

def link_images_for_split(split_dir: Path):
    labels_dir = split_dir / "labels"
    images_out = split_dir / "images"
    images_out.mkdir(exist_ok=True)

    count = 0
    for label_file in labels_dir.glob("*.txt"):
        image_file = find_image(label_file.stem)
        if image_file is None:
            print(f"  [!] No image found for {label_file.name}, skipping")
            continue
        (images_out / image_file.name).symlink_to(image_file.resolve())
        count += 1

    print(f"{split_dir}: linked {count} images")

print("Linking images into each split...")
link_images_for_split(train_yolo_dir)
link_images_for_split(test_yolo_dir)

with open(train_yolo_dir / "data.yaml") as f:
    existing_config = yaml.safe_load(f)

class_names = existing_config["names"]
num_classes = existing_config["nc"]

combined_config = {
    "train": str(train_yolo_dir / "images"),
    "val": str(test_yolo_dir / "images"),
    "nc": num_classes,
    "names": class_names,
}

data_yaml_path = Path("data.yaml")
with open(data_yaml_path, "w") as f:
    yaml.dump(combined_config, f)

print(f"\nWrote {data_yaml_path}")

model = YOLO("yolov8n.pt")

model.train(
    data=str(data_yaml_path),
    epochs=5,
    imgsz=640,
)

metrics = model.val(data=str(data_yaml_path), split="val")
print("Evaluation metrics:", metrics.results_dict)
```

Run the script with:

```bash
python train_yolo.py
```

Or, if you use `uv`:

```bash
uv run train_yolo.py
```

After training, Ultralytics evaluates the model on the `test_yolo` split and prints the evaluation metrics. You should see output similar to this:

```text
Validating runs/detect/train/weights/best.pt...

Model summary (fused): 73 layers, 3,151,904 parameters, 8.7 GFLOPs

                 Class     Images  Instances      Box(P)      R      mAP50  mAP50-95
                   all         18        127      0.025   0.0185    0.00504   0.00307
              backpack          1          1          0        0          0         0
               bicycle          1          2          0        0          0         0
                   bus          2          2          0        0          0         0
                   car         18         81       0.25    0.185     0.0504    0.0307
               giraffe          1          2          0        0          0         0
            motorcycle          2          5          0        0          0         0
                person          5          9          0        0          0         0
             stop sign          2          2          0        0          0         0
         traffic light          2          4          0        0          0         0
                 truck         11         19          0        0          0         0

Speed: 0.6ms preprocess, 121.6ms inference, 0.0ms loss, 1.0ms postprocess per image

Results saved to runs/detect/train
Results saved to runs/detect/val

Evaluation metrics: {
  'metrics/precision(B)': 0.025,
  'metrics/recall(B)': 0.0185,
  'metrics/mAP50(B)': 0.0050,
  'metrics/mAP50-95(B)': 0.0031,
  'fitness': 0.0031
}
```

The exact values will depend on the dataset size, selected classes, annotation quality, model size, and number of training epochs. In this tutorial, the goal is not to train a highly accurate model, but to verify that the exported YOLO dataset can be used successfully for training and evaluation.

## Conclusion

In this tutorial, we prepared a YOLO object detection dataset from raw traffic CCTV images using LightlyStudio.

We started by loading the images into LightlyStudio and using the embedding plot to explore the dataset. Then, we identified outliers, removed near-duplicate samples, and used Query Filters to tag valid images for the dataset. After curating the samples, we used the YOLO inference plugin to generate initial annotations and manually reviewed them to improve annotation quality.

Next, we split the curated samples into training and test sets, exported both splits in YOLO format, and ran a short Ultralytics training and evaluation job to verify that the exported dataset could be used by a standard YOLO training pipeline.

This workflow provides a practical way to go from a folder of raw images to a curated, annotated, and trainable YOLO dataset. From here, you can continue improving the dataset by reviewing more annotations, adding more diverse samples, adjusting the train/test split, or running a longer YOLO training job.
