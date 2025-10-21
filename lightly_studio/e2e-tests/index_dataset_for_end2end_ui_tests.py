"""End-to-end demonstration of the lightly_studio dataset loading and UI.

This module provides a simple example of how to load a COCO instance
segmentation dataset and launch the UI application for exploration and
visualization.
"""

# We import the DatasetLoader class from the lightly_studio module
from lightly_studio import DatasetLoader, db_manager
from lightly_studio.api.features import lightly_studio_active_features

# Clean up an existing database
db_manager.connect(cleanup_existing=True)

# Create a DatasetLoader instance
loader = DatasetLoader()

# We point to the annotations json file and the input images folder.
# Defined dataset is processed here to be available for the UI application.
loader.from_coco_instance_segmentations(
    annotations_json_path="datasets/coco-128/instances_train2017.json",
    img_dir="datasets/coco-128/images",
)

# TODO(Horatiu, 08/2025): Current e2e tests should not use the few shot classifier implementation.
# Without the few shot classifier feature enabled tests timeout on CI.
lightly_studio_active_features.append("fewShotClassifierEnabled")
# We start the UI application on port 8001
loader.start_gui()
