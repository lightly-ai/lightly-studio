"""Example of how to add samples in coco format to a dataset."""

import random

from environs import Env

import lightly_studio as ls
from lightly_studio import db_manager
from lightly_studio.models.tag import TagCreate
from lightly_studio.resolvers import annotation_resolver, collection_resolver, tag_resolver

# Read environment variables
env = Env()
env.read_env()

# Cleanup an existing database
db_manager.connect(cleanup_existing=True)

# Define data paths
annotations_json = env.path("EXAMPLES_COCO_JSON_PATH", "/path/to/your/dataset/annotations.json")
images_path = env.path("EXAMPLES_COCO_IMAGES_PATH", "/path/to/your/dataset")

# Create a DatasetLoader from a path
dataset = ls.ImageDataset.create()
dataset.add_samples_from_coco(
    annotations_json=annotations_json,
    images_path=images_path,
    annotation_type=ls.AnnotationType.SEGMENTATION_MASK,
)

# LIG-9521 prototype: create two annotation tags with random annotations each.
rng = random.Random(0)
annotation_collections = collection_resolver.get_annotation_collections(
    session=dataset.session, parent_collection_id=dataset.collection_id
)
for annotation_collection in annotation_collections:
    annotation_sample_ids = sorted(
        annotation_resolver.get_sample_ids(
            session=dataset.session, collection_id=annotation_collection.collection_id
        )
    )
    for tag_name, tag_size in [("random-200", 200), ("random-400", 400)]:
        tag = tag_resolver.create(
            session=dataset.session,
            tag=TagCreate(
                name=tag_name,
                collection_id=annotation_collection.collection_id,
                kind="annotation",
            ),
        )
        tag_resolver.add_sample_ids_to_tag_id(
            session=dataset.session,
            tag_id=tag.tag_id,
            sample_ids=rng.sample(
                annotation_sample_ids, min(tag_size, len(annotation_sample_ids))
            ),
        )

ls.start_gui()
