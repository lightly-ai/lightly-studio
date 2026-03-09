"""Indexing dataset with creating groups."""

from pathlib import Path

import lightly_studio as ls
from lightly_studio.core.group.group_dataset import GroupDataset

DATASET_DIR = Path("datasets/midv_2020_10_samples")

# Debug print contents of the parent folder
print(f"Contents of {DATASET_DIR.parent}:")
for item in DATASET_DIR.parent.iterdir():
    print(f" - {item.name} {'(dir)' if item.is_dir() else '(file)'}")

# Debug print contents of the folder
print(f"Contents of {DATASET_DIR}:")
for item in DATASET_DIR.iterdir():
    print(f" - {item.name} {'(dir)' if item.is_dir() else '(file)'}")

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

print(f"Adding samples from {DATASET_DIR}...")

# Fill components with samples
for photo_path in Path(DATASET_DIR / "photo").glob("*.jpg"):
    print(f"Processing {photo_path.name}...")
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
