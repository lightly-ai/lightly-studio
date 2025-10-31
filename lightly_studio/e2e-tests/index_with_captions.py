"""End-to-end demonstration of the lightly_studio dataset loading and UI.

This module provides a simple example of how to load a COCO instance
segmentation dataset and launch the UI application for exploration and
visualization.
"""

# We import the DatasetLoader class from the lightly_studio module
import lightly_studio as ls
from lightly_studio.resolvers import caption_resolver

# Create a DatasetLoader instance
dataset = ls.Dataset.create()
dataset.add_samples_from_coco_caption(
    annotations_json="datasets/coco-128/captions_train2017.json",
    images_path="datasets/coco-128/images",
)

# Display some details about the captions
samples_with_captions_result = caption_resolver.get_all_captions_by_sample(
    session=dataset.session, dataset_id=dataset.dataset_id
)
print(samples_with_captions_result.total_count)

for samples in samples_with_captions_result.samples[:10]:
    for caption in samples.captions:
        print(caption.text)

ls.start_gui()
