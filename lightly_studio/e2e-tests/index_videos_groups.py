"""Indexing dataset with creating group with videos."""

from pathlib import Path

import lightly_studio as ls
from lightly_studio.core.group.group_dataset import GroupDataset

DATASET_DIR = Path("datasets/midv_2020_10_samples")

# Cleanup an existing database
ls.db_manager.connect(cleanup_existing=True)

# Create component with only 1 video sample type
dataset = GroupDataset.create(
    components=[
        ("clips_video", ls.SampleType.VIDEO),
    ]
)

# Fill component with samples
for vid_path in Path(DATASET_DIR / "clips_video").glob("*.mp4"):
    dataset.add_group_sample(
        components={
            "clips_video": ls.CreateVideo(path=str(vid_path)),
        }
    )

ls.start_gui()
