"""Example of how to add samples in coco format to a dataset."""

from pathlib import Path

import lightly_studio as ls
from lightly_studio.core.create_image import CreateImage
from lightly_studio.core.create_video import CreateVideo
from lightly_studio.core.group_dataset import GroupDataset
from lightly_studio.resolvers import collection_resolver, group_resolver

# EDIT THIS
DATASET_DIR = Path("datasets/groups_dataset_example")

# Cleanup an existing database
ls.db_manager.connect(cleanup_existing=True)

# Create a DatasetLoader from a path
dataset = GroupDataset.create(
    components=[
        ("fish", ls.SampleType.IMAGE),
        ("coco", ls.SampleType.IMAGE),
        ("vid", ls.SampleType.VIDEO),
    ]
)
session = dataset.session

# Add samples to the dataset
# TODO: Switch away from resolvers
component_collections = collection_resolver.get_group_components(
    session=session,
    parent_collection_id=dataset.dataset_id,
)
comp_filenames = [
    ("fish1.jpg", "coco1.jpg", "vid1.mp4"),
    ("fish2.jpg", "coco2.jpg", "vid2.mp4"),
    ("fish3.jpg", "coco3.jpg", "vid3.mp4"),
]
for comp_filename in comp_filenames:
    fish_path = str(DATASET_DIR / comp_filename[0])
    coco_path = str(DATASET_DIR / comp_filename[1])
    vid_path = str(DATASET_DIR / comp_filename[2])

    fish_id = CreateImage(path=fish_path).create_in_collection(
        session=session,
        collection_id=component_collections["fish"].collection_id,
    )
    coco_id = CreateImage(path=coco_path).create_in_collection(
        session=session,
        collection_id=component_collections["coco"].collection_id,
    )
    vid_id = CreateVideo(path=vid_path).create_in_collection(
        session=session,
        collection_id=component_collections["vid"].collection_id,
    )

    group_resolver.create_many(
        session=session,
        collection_id=dataset.dataset_id,
        groups=[(fish_id, coco_id, vid_id)],
    )


# Optional: Print out the samples
for sample in dataset:
    print(f"Group sample ID: {sample.sample_id}")
    print(
        f"Group components: {sample['fish'].file_name}, {sample['coco'].file_name}, {sample['vid'].file_name}"
    )

# Enable when frontend is ready
ls.start_gui()
