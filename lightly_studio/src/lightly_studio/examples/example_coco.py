"""Example of how to add samples in coco format to a dataset."""

import random

from environs import Env

import lightly_studio as ls
from lightly_studio import db_manager
from lightly_studio.models.tag import TagCreate
from lightly_studio.resolvers import (
    annotation_resolver,
    collection_resolver,
    metadata_resolver,
    tag_resolver,
)

# Read environment variables
env = Env()
env.read_env()

# Cleanup an existing database
db_manager.connect(db_file="coco.db", cleanup_existing=True)

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

# LIG-9521 prototype: create two annotation tags with random annotations each, and give
# every annotation exactly one metadata["tag"] value derived from its tag membership
# ("no tag", "random-200", "random-400", "random-both"). Dummy data for testing
# metadata colouring in the embedding plot.
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
    tagged_ids_by_name: dict[str, set] = {}
    for tag_name, tag_size in [("random-200", 200), ("random-400", 400)]:
        tagged_ids = rng.sample(annotation_sample_ids, min(tag_size, len(annotation_sample_ids)))
        tagged_ids_by_name[tag_name] = set(tagged_ids)
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
            sample_ids=tagged_ids,
        )

    sample_metadata = []
    for sample_id in annotation_sample_ids:
        in_200 = sample_id in tagged_ids_by_name["random-200"]
        in_400 = sample_id in tagged_ids_by_name["random-400"]
        if in_200 and in_400:
            metadata_tag = "random-both"
        elif in_200:
            metadata_tag = "random-200"
        elif in_400:
            metadata_tag = "random-400"
        else:
            metadata_tag = "no tag"
        sample_metadata.append((sample_id, {"tag": metadata_tag}))
    metadata_resolver.bulk_update_metadata(
        session=dataset.session, sample_metadata=sample_metadata
    )

ls.start_gui()
