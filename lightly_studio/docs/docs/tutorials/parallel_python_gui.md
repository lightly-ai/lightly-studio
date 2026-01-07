# Parallel Python and GUI

Use the background GUI helpers to keep the web UI running while your Python code
continues to execute. This is especially useful in notebooks where you want to
keep exploring or updating the dataset after the GUI starts. You can explore the dataset interactively in the GUI, then decided to add some metadata or do selections in Python, and then continue exploring the updated dataset in the GUI without having to restart it.

The following example works best in a Jupyter notebook environment:

### Cell 1: Setup
```python
import lightly_studio as ls
from lightly_studio.utils import download_example_dataset
```

### Cell 2: Create a dataset from COCO data
```python
dataset_path = download_example_dataset(download_dir="dataset_examples")
dataset = ls.Dataset.create("coco_instance_segmentation_dataset")
dataset.add_samples_from_coco(
    annotations_json=f"{dataset_path}/coco_subset_128_images/instances_train2017.json",
    images_path=f"{dataset_path}/coco_subset_128_images/images",
    annotation_type=ls.AnnotationType.INSTANCE_SEGMENTATION,
)
```

### Cell 3: Start the GUI in the background
```python
ls.start_gui_background()
```
Now you can click on the link printed in the output to open the GUI in your browser.

### Cell 4: Run python code while the GUI stays open.
```python
for i, sample in enumerate(dataset):
    sample.metadata["index_in_dataset"] = i

dataset.query().selection().metadata_weighting(
  n_samples_to_select=10,
  selection_result_tag_name="top_10_by_metadata_weighting",
  metadata_key="index_in_dataset",
)
```
After a refresh, you can see the updated metadata and selection in the GUI.


### Cell 5: Stop the background GUI server
```python
ls.stop_gui_background()
```

Notes:

- Call `start_gui_background()` before interacting with the GUI and
  `stop_gui_background()` when you are done.
