# Tags

Tags let you organize samples within a dataset. One sample can belong to multiple tags. Use tags to
track curation progress, mark samples for review, define train/val/test splits, or prepare subsets
for export. Tags can be created manually in the GUI or programmatically through the Python API.

## Tags in the GUI

The left sidebar lists all tags in the current view. Select one or more to show samples matching
any of them.

To assign tags, first select samples in the grid view. Then, in the left sidebar, create a new tag
or assign an existing one. Tags can be removed in sample details view.

!!! tip "Bulk selection"
    Hold down the `Shift` key to select a range of samples.

<video autoplay loop muted playsinline controls style="width: 100%;">
  <source src="https://storage.googleapis.com/lightly-public/studio/tag_workflow.mp4" type="video/mp4">
</video>

## Tags in Python

### Tags on individual samples

Access and modify tags on a `Sample` object using the `tags` property or the helper methods:

```python
# Assuming `dataset` is a lightly_studio dataset object
dataset = ...

for sample in dataset:
    print(sample.tags)  # e.g. {'train', 'reviewed'}
    sample.add_tag("reviewed")  # adds "reviewed" tag
    sample.remove_tag("old-label")  # removes "old-label" tag
    sample.tags = {"train", "high-quality"}  # replaces all tags with the new set
```

### Tagging a query result

`DatasetQuery.add_tag` applies a tag to every sample matched by the query.
The tag is created automatically if it does not exist, and samples that already carry the tag are
left unchanged.

```python
import lightly_studio as ls
from lightly_studio.core.dataset_query import VideoSampleField

# The example query assumes `dataset` is a VideoDataset object
dataset = ls.VideoDataset.load()

# Tag all large videos
dataset.match(VideoSampleField.width > 1920).add_tag("high-res")
```

See [Search and Filter](search_and_filter.md#query-in-python) for the full query API.

### Tagging when loading data

When working with images, the `ImageDataset` class provides convenience features to automatically
tag samples during loading.

#### By folder structure

When loading images from a folder, pass `tag_depth=1` to automatically create a tag for each image
based on its parent directory's name.

```python
import lightly_studio as ls

dataset = ls.ImageDataset.load()
dataset.add_images_from_path(path="/data/images", tag_depth=1)
```

Given this layout, each sample receives a tag matching its folder:

```
/data/images/
├── cats/
│   ├── cat1.jpg   → tagged "cats"
│   └── cat2.jpg   → tagged "cats"
└── dogs/
    ├── dog1.jpg   → tagged "dogs"
    └── dog2.jpg   → tagged "dogs"
```

The default is `tag_depth=0`, which skips automatic tagging.

#### By dataset split

Methods that load annotated data accept an optional `split` parameter.
When provided, every sample loaded in that call receives a tag with the split name.

```python
dataset.add_samples_from_coco(
    annotations_json="/data/train.json",
    images_path="/data/images",
    split="train",
)
```

In the case of YOLO format, splits are encoded in the format. The split to load can be specified
using the `input_split` parameter, the loaded samples will be automatically tagged.

```python
dataset.add_samples_from_yolo(
    data_yaml="/data/yolo/data.yaml",
    input_split="train",
)
```

Check [Dataset](../api/dataset.md) Python API docs for a full list of methods that support
split loading.
