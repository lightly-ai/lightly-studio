"""Indexing dataset with creating group with videos."""

from pathlib import Path

import lightly_studio as ls
from lightly_studio.core.group.group_dataset import GroupDataset

DATASET_DIR = Path("datasets/midv_2020_10_samples")

# Cleanup an existing database
ls.db_manager.connect(cleanup_existing=True)

# Create a DatasetLoader from a path
dataset = GroupDataset.create(
    components=[
        ("clips_video", ls.SampleType.VIDEO),
    ]
)

# Add samples to the dataset using example_group
example_group = {
    "clips_video": "alb_id.mp4",
}
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
for comp_filename in comp_filenames:
    vid_path = str(DATASET_DIR / "clips_video" / comp_filename)

    dataset.add_group_sample(
        components={
            "clips_video": ls.CreateVideo(path=str(vid_path)),
        }
    )

# Enable when frontend is ready
ls.start_gui()
