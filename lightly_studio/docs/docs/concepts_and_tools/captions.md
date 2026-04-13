# Captions

Captions are text descriptions associated with samples in your dataset. Each sample can have one or
more captions. Captions are commonly used as training data for vision-language models.
You can add, edit, and delete captions in the GUI or through the Python API.

## Captions in the GUI

### Sample detail view

In sample detail view, captions are displayed in the side panel. Toggle `Edit Annotations` button
to enable caption editing.

<video autoplay loop muted playsinline controls style="width: 100%;">
  <source src="https://storage.googleapis.com/lightly-public/studio/detail_view_captions.mp4" type="video/mp4">
</video>

### Captions view

Use the navigation menu at the top to switch to the `Captions` view, which displays captions
for all samples that have captions. Toggle `Edit Annotations` button to enable caption editing.

<video autoplay loop muted playsinline controls style="width: 100%;">
  <source src="https://storage.googleapis.com/lightly-public/studio/captions_view.mp4" type="video/mp4">
</video>

## Captions in Python

### Captions on individual samples

Access and modify captions on a `Sample` object using the `captions` property or the helper methods.
These methods can also be used to export the captions manually.

```python
# Assuming `dataset` is a lightly_studio dataset object
dataset = ...

for sample in dataset:
    # Read sample captions. Returns list[str].
    print(sample.captions)

    # Add one or more captions to the sample
    sample.add_caption("A cat on a mat")
    sample.add_captions(["A cat on a mat", "Tabby cat resting indoors"])

    # Replace all captions with a new list of captions
    sample.captions = ["Updated caption text"]
```

### The COCO caption format

Image datasets in COCO caption format can be loaded with `add_samples_from_coco_caption`. This
method imports both the images and their associated captions.

```python
import lightly_studio as ls

dataset = ls.ImageDataset.create()
dataset.add_samples_from_coco_caption(
    annotations_json="/data/captions.json",
    images_path="/data/images",
)
```

The COCO caption JSON is expected to have the following structure:

```json
{
  "images": [
    {"id": 1, "file_name": "cat.jpg", "width": 640, "height": 480}
  ],
  "annotations": [
    {"id": 1, "image_id": 1, "caption": "A cat on a mat"},
    {"id": 2, "image_id": 1, "caption": "Tabby cat resting indoors"}
  ]
}
```

Similarly, image datasets with captions can be exported to COCO caption format:

```python
import lightly_studio as ls

dataset = ls.ImageDataset.load()
dataset.export().to_coco_captions(output_json="/data/captions_export.json")
```
