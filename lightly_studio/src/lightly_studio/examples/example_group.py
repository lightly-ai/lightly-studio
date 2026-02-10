"""Example of how to create a group dataset."""

from pathlib import Path

from environs import Env

import lightly_studio as ls
from lightly_studio.resolvers import collection_resolver

# Read environment variables
env = Env()
env.read_env()

# Set the path to the dataset directory
dataset_path = env.path("EXAMPLES_MIDV_PATH", "/path/to/midv/dataset")

# Cleanup an existing database
ls.db_manager.connect(cleanup_existing=True)

# Create a DatasetLoader from a path
dataset = ls.GroupDataset.create(
    components=[
        ("photo", ls.SampleType.IMAGE),
        ("scan_upright", ls.SampleType.IMAGE),
        ("clips_video", ls.SampleType.VIDEO),
    ]
)

# Populate the dataset with samples
for photo_path in Path(dataset_path / "photo").glob("*.jpg"):
    scan_upright_path = dataset_path / "scan_upright" / photo_path.name
    clips_video_path = dataset_path / "clips_video" / photo_path.with_suffix(".mp4").name

    dataset.add_group_sample(
        components={
            "photo": ls.CreateImage(path=str(photo_path)),
            "scan_upright": ls.CreateImage(path=str(scan_upright_path)),
            "clips_video": ls.CreateVideo(path=str(clips_video_path)),
        }
    )

print(f"Created group dataset with {len(list(iter(dataset)))} samples.")

# Enable when frontend is ready
print(f"Dataset ID: {dataset.dataset_id}")
comp_cols = collection_resolver.get_group_components(
    session=dataset.session,
    parent_collection_id=dataset.dataset_id,
)
photo_col_id = comp_cols["photo"].collection_id
scan_upright_col_id = comp_cols["scan_upright"].collection_id
clips_video_col_id = comp_cols["clips_video"].collection_id
print()
print(f"http://localhost:8001/datasets/{photo_col_id}/image/{photo_col_id}")
print(f"http://localhost:8001/datasets/{scan_upright_col_id}/image/{scan_upright_col_id}")
print(f"http://localhost:8001/datasets/{clips_video_col_id}/video/{clips_video_col_id}")
print()
ls.start_gui()
