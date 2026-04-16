# Export

Export lets you save annotations and file paths from your dataset in common formats.
Exports can be triggered from the GUI or through the Python API. You can export an entire dataset
or a filtered subset based on tags, or other criteria when using the Python API.

The following export formats are supported:

| Format | Content | File type |
|---|---|---|
| Sample Filenames | Absolute file paths of selected samples | TXT |
| COCO Object Detection | Bounding box annotations | JSON |
| COCO Instance Segmentation | Segmentation masks with bounding boxes | JSON |
| COCO Captions | Image captions | JSON |
| Pascal VOC Semantic Segmentation | Per-pixel class masks | PNG masks + class map |
| YouTube-VIS Instance Segmentation | Video instance segmentation tracks | JSON |

## Export in the GUI

Open the export dialog from the `Menu` button in the top-right corner of any grid view
and select `Export`. The dialog shows a dropdown with all available formats for the current dataset.

![Export format dropdown](https://storage.googleapis.com/lightly-public/studio/export_dialog_dropdown.png){width=80%}

### Exporting annotations

For annotation formats (`Image Object Detections`, `Image Instance Segmentations`,
`Image Semantic Segmentations`, `Image Captions`, `YouTube-VIS Video Instance Segmentations`),
select the format and click `Download`. A zip file is created if the export includes multiple files.
The export includes all samples in the dataset.

![Export object detections](https://storage.googleapis.com/lightly-public/studio/export_dialog_object_detections.png){width=60%}

### Exporting sample filenames by tag

The `Image Filenames` option supports tag-based filtering. Tick `Inverse selection` to export
samples that do not have the selected tag.

![Export filenames by tag](https://storage.googleapis.com/lightly-public/studio/export_dialog_filenames.png){width=60%}

## Export in Python

### Export a dataset

Call `dataset.export()` to get an export object, then call a format-specific method on it.
The export methods depend on the dataset type, see
[Dataset export reference](../api/dataset.md#imagedatasetexport)
for details.

```python
import lightly_studio as ls

# Image dataset export
dataset = ls.ImageDataset.load()
dataset.export().to_coco_object_detections("detections.json")
dataset.export().to_coco_instance_segmentations("segmentations.json")
dataset.export().to_coco_captions("captions.json")
dataset.export().to_pascalvoc_instance_segmentation("pascalvoc_output_dir/")

# Video dataset export
dataset = ls.VideoDataset.load()
dataset.export().to_youtube_vis_instance_segmentation("youtube_vis.json")
```

### Export a filtered subset

Pass a `DatasetQuery` to `export()` to export only matching samples. Queries support
filtering, ordering, and slicing — see [Search and Filter](search_and_filter.md#query-in-python)
for the full query API.

```python
import lightly_studio as ls
from lightly_studio.core.dataset_query import ImageSampleField

dataset = ls.ImageDataset.load()

# Export only samples taller than 500 pixels
query = dataset.query().match(ImageSampleField.height > 500)
dataset.export(query).to_coco_object_detections("tall_images.json")
```
