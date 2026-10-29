# Train a Detector with LightlyTrain

This page shows the full loop for object detection:

1. Export images and annotations from LightlyStudio.
2. Train a detector with [LightlyTrain](https://docs.lightly.ai/train/).
3. Predict on the dataset and add the predictions back as a new annotation source.

Install LightlyTrain in the environment that you use for training:

```bash
pip install lightly-train
```

## 1. Export images and annotations

### In the GUI

1. Filter the grid to the images that you want to train on, for example by the tag `train`.
2. Open `Menu` > `Export` and select `Image Object Detections (COCO)`.
3. Select `Include images` and click `Download`.
4. Unzip `coco_export.zip`. It contains `annotations.json` and an `images` folder.

Images from cloud storage are downloaded into the zip file, so the training machine does not need
access to the bucket.

### In Python

Export each tag to its own folder. Use one tag for training and one tag for validation.

```python
import lightly_studio as ls
from lightly_studio.core.dataset_query import ImageSampleField

dataset = ls.ImageDataset.load("my_dataset")
for split in ["train", "val"]:
    query = dataset.query().match(ImageSampleField.tags.contains(split))
    dataset.export(query).to_coco_object_detections(
        f"export/{split}/annotations.json", include_images=True
    )
```

Each `file_name` in `annotations.json` is relative to the `images` folder. Images keep their
folder structure, so two images with the same file name in different folders do not collide.

## 2. Train

```python
import lightly_train

lightly_train.train_object_detection(
    out="out/detector",
    model="ltdetrv2-s-coco",
    data={
        "format": "coco",
        "train": {
            "annotations": "export/train/annotations.json",
            "images": "export/train/images",
        },
        "val": {
            "annotations": "export/val/annotations.json",
            "images": "export/val/images",
        },
    },
)
```

The best checkpoint is in `out/detector/exported_models/exported_best.pt`. See the
[LightlyTrain object detection docs](https://docs.lightly.ai/train/stable/object_detection.html)
for the training options.

## 3. Predict and add the predictions to LightlyStudio

Run the model on every image of the dataset and add the boxes to a new annotation source,
`model_v1`. The model returns the category IDs of the export, so the class names come from
`annotations.json`.

```python
import json
from pathlib import Path

import fsspec
import lightly_studio as ls
import lightly_train
from PIL import Image
from lightly_studio.core.annotation.annotation_create import CreateObjectDetection

dataset = ls.ImageDataset.load("my_dataset")
model = lightly_train.load_model("out/detector/exported_models/exported_best.pt")
categories = json.loads(Path("export/train/annotations.json").read_text())["categories"]
class_names = {category["id"]: category["name"] for category in categories}

for sample in dataset.query().to_list():
    with fsspec.open(sample.file_path_abs, "rb") as f:
        image = Image.open(f).convert("RGB")
    result = model.predict(image, threshold=0.5)
    sample.add_annotations(
        [
            CreateObjectDetection(
                class_name=class_names[label.item()],
                x=int(x0),
                y=int(y0),
                width=int(x1 - x0),
                height=int(y1 - y0),
                confidence=score.item(),
            )
            for label, (x0, y0, x1, y1), score in zip(
                result["labels"], result["bboxes"].tolist(), result["scores"]
            )
        ],
        annotation_source="model_v1",
    )
```

Open the dataset in LightlyStudio and select the `model_v1` annotation source to see the
predictions. To compare them with the ground truth, see [Model Evaluation](evaluation.md).

If you already have the predictions in a COCO file, add them in one call. The `file_name` values
must match the image paths relative to `images_root`:

```python
dataset.add_annotations_from_coco(
    annotations_json="predictions.json",
    images_root="/path/to/images",
    annotation_source="model_v1",
)
```
