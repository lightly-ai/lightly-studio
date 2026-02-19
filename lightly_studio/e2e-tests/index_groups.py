"""Indexing dataset with creating groups."""

from pathlib import Path

import lightly_studio as ls
from lightly_studio.core.group.group_dataset import GroupDataset

DATASET_DIR = Path("datasets/midv_2020_10_samples")

# Cleanup an existing database
ls.db_manager.connect(cleanup_existing=True)

# Create components
dataset = GroupDataset.create(
    components=[
        ("photo", ls.SampleType.IMAGE),
        ("scan_upright", ls.SampleType.IMAGE),
        ("clips_video", ls.SampleType.VIDEO),
    ]
)

# Fill components with samples
for photo_path in Path(DATASET_DIR / "photo").glob("*.jpg"):
    scan_upright_path = DATASET_DIR / "scan_upright" / photo_path.name
    clips_video_path = DATASET_DIR / "clips_video" / photo_path.with_suffix(".mp4").name

    dataset.add_group_sample(
        components={
            "photo": ls.CreateImage(path=str(photo_path)),
            "scan_upright": ls.CreateImage(path=str(scan_upright_path)),
            "clips_video": ls.CreateVideo(path=str(clips_video_path)),
        }
    )

ls.start_gui()
