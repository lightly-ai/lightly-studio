"""Example of how to add samples in coco caption format to a dataset."""

import lightly_studio as ls
from lightly_studio import db_manager
from lightly_studio.resolvers import caption_resolver

# Cleanup an existing database
db_manager.connect(cleanup_existing=True)

# Create a DatasetLoader from a path
dataset = ls.Dataset.create()
dataset.add_samples_from_coco_caption(
    annotations_json="/path/to/your/dataset/annotations.json",
    images_path="/path/to/your/dataset",
)

# Display some details about the captions
captions_result = caption_resolver.get_all(session=dataset.session, dataset_id=dataset.dataset_id)
print(captions_result.total_count)

for caption in captions_result.captions[:10]:
    print(caption)

ls.start_gui()
