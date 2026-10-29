# Export

Export lets you save annotations and file paths from your dataset in common formats.
Exports can be triggered from the GUI or through the Python API. You can export an entire dataset
or a filtered subset using collection filters, or other criteria when using the Python API.

The following export formats are supported:

| Format | Content | File type |
|---|---|---|
| Sample Filenames | Absolute file paths of selected samples | TXT |
| Classification CSV | Image and whole-video classification annotations and confidence scores | CSV |
| COCO Object Detection | Bounding box annotations, optionally with the images | JSON, or JSON + images (zipped) |
| YOLO Object Detection | Bounding box annotations | TXT labels + `data.yaml` (zipped) |
| COCO Segmentation Mask | Segmentation masks with bounding boxes | JSON |
| COCO Captions | Image captions | JSON |
| Pascal VOC Semantic Segmentation | Per-pixel class masks | PNG masks + class map |
| YouTube-VIS Segmentation Mask | Video segmentation mask tracks | JSON |

## Export in the GUI

Open the export dialog from the `Menu` button in the top-right corner of any grid view
and select `Export`. The dialog shows a dropdown with all available formats for the current dataset.

![Export format dropdown](https://storage.googleapis.com/lightly-public/studio/export_dialog_dropdown.png){width=80%}

### Exporting annotations

For annotation formats (`Image Classifications (CSV)`, `Video Classifications (CSV)`,
`Image Object Detections (COCO)`,
`Image Object Detections (YOLO)`,
`Image Segmentation Mask (COCO)`, `Image Segmentation Mask (PASCAL VOC)`, `Image Captions`,
`YouTube-VIS Video Segmentation Masks`),
select the format and click `Download`. A zip file is created if the export includes multiple files.
The export includes the samples that match your current filters, and the dialog states how many.
To export one tag, filter by that tag before you open the dialog.

![Export object detections](https://storage.googleapis.com/lightly-public/studio/export_dialog_object_detections.png){width=60%}

### Exporting images with the annotations

For `Image Object Detections (COCO)`, select `Include images` to download the images together with
the annotations. The zip file contains `annotations.json` and an `images` folder. Each `file_name`
in `annotations.json` is relative to the `images` folder, so the export is ready to train on, also
when the images are in cloud storage. To train a detector on the export, see
[Train a Detector with LightlyTrain](train_with_lightlytrain.md).

### Exporting sample filenames

The `Image Filenames` option exports the filenames of all samples that match the active collection
filters. Apply filters in the collection view before opening the export dialog to limit the export
to a specific subset.

![Export sample filenames](https://storage.googleapis.com/lightly-public/studio/export_dialog_filenames.png){width=60%}

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
dataset.export().to_csv_classifications("classifications.csv")
dataset.export().to_coco_object_detections("detections.json")
# Copy the images to "export/images" and reference them relative to that folder
dataset.export().to_coco_object_detections("export/annotations.json", include_images=True)
dataset.export().to_yolo_object_detections("yolo_output_dir/")
dataset.export().to_coco_segmentation_masks("segmentations.json")
dataset.export().to_coco_captions("captions.json")
dataset.export().to_pascalvoc_segmentation_mask("pascalvoc_output_dir/")

# Video dataset export
dataset = ls.VideoDataset.load()
dataset.export().to_csv_classifications("classifications.csv")
dataset.export().to_youtube_vis_segmentation_mask("youtube_vis.json")
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
