"""Example of how to add samples in coco caption format to a dataset."""

from environs import Env

import lightly_studio as ls
from lightly_studio import db_manager
from lightly_studio.resolvers import caption_resolver

# Read environment variables
env = Env()
env.read_env()

# Cleanup an existing database
db_manager.connect(cleanup_existing=True)

# Define data paths
annotations_json = env.path(
    "EXAMPLES_COCO_CAPTION_JSON_PATH", "/path/to/your/dataset/annotations.json"
)
images_path = env.path("EXAMPLES_COCO_CAPTION_IMAGES_PATH", "/path/to/your/dataset")


# Create a DatasetLoader from a path
dataset = ls.Dataset.create()
dataset.add_samples_from_coco_caption(
    annotations_json=annotations_json,
    images_path=images_path,
)

# Display some details about the captions
captions_result = caption_resolver.get_all(session=dataset.session, dataset_id=dataset.dataset_id)
print(captions_result.total_count)

for caption in captions_result.captions[:10]:
    print(caption)

ls.start_gui()
