"""Example of how to add video samples in groups to a dataset."""

from pathlib import Path

import lightly_studio as ls
from lightly_studio.core.group.group_dataset import GroupDataset
from lightly_studio.core.video.create_video import CreateVideo
from lightly_studio.resolvers import collection_resolver, group_resolver

# EDIT THIS
DATASET_DIR = Path("datasets/midv_2020_10_samples")

# Cleanup an existing database
ls.db_manager.connect(cleanup_existing=True)

# Create a DatasetLoader from a path
dataset = GroupDataset.create(
    components=[
        ("clips_video", ls.SampleType.VIDEO),
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
    "alb_id.mp4",
    "aze_passport.mp4",
    "esp_id.mp4",
    "est_id.mp4",
    "fin_id.mp4",
    "grc_passport.mp4",
    "lva_passport.mp4",
    "rus_internalpassport.mp4",
    "srb_passport.mp4",
    "svk_id.mp4",
]
groups = []
for comp_filename in comp_filenames:
    vid_path = str(DATASET_DIR / "clips_video" / comp_filename)

    vid_id = CreateVideo(path=vid_path).create_in_collection(
        session=session,
        collection_id=component_collections["clips_video"].collection_id,
    )
    groups.append((vid_id,))

group_resolver.create_many(
    session=session,
    collection_id=dataset.dataset_id,
    groups=groups,
)


# Optional: Print out the samples
for sample in dataset:
    print(f"Group sample ID: {sample.sample_id}")
    vid_comp = sample["clips_video"]
    if vid_comp:
        print(f"Group component: {vid_comp.file_name}")  # type: ignore[attr-defined]

# Enable when frontend is ready
ls.start_gui()
