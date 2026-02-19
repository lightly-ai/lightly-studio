"""
Example of how to create a grouped dataset from MIDV-style component folders
and add image/video samples to it.
"""

from pathlib import Path

import lightly_studio as ls
from lightly_studio.core.group.group_dataset import GroupDataset

# EDIT THIS
DATASET_DIR = Path("datasets/midv_2020_10_samples")

# Cleanup an existing database
ls.db_manager.connect(cleanup_existing=True)

# Create a DatasetLoader from a path
dataset = GroupDataset.create(
    components=[
        ("photo", ls.SampleType.IMAGE),
        ("scan_upright", ls.SampleType.IMAGE),
        ("clips_video", ls.SampleType.VIDEO),
    ]
)

# Create components
example_group = {
    "photo": "alb_id.jpg",
    "scan_upright": "alb_id.jpg",
    "clips_video": "alb_id.mp4",
}
comp_filenames = [
    ("alb_id.jpg", "alb_id.jpg", "alb_id.mp4"),
    ("aze_passport.jpg", "aze_passport.jpg", "aze_passport.mp4"),
    ("esp_id.jpg", "esp_id.jpg", "esp_id.mp4"),
    ("est_id.jpg", "est_id.jpg", "est_id.mp4"),
    ("fin_id.jpg", "fin_id.jpg", "fin_id.mp4"),
    ("grc_passport.jpg", "grc_passport.jpg", "grc_passport.mp4"),
    ("lva_passport.jpg", "lva_passport.jpg", "lva_passport.mp4"),
    ("rus_internalpassport.jpg", "rus_internalpassport.jpg", "rus_internalpassport.mp4"),
    ("srb_passport.jpg", "srb_passport.jpg", "srb_passport.mp4"),
    ("svk_id.jpg", "svk_id.jpg", "svk_id.mp4"),
]

for comp_filename in comp_filenames:
    photo_path = str(DATASET_DIR / "photo" / comp_filename[0])
    scan_path = str(DATASET_DIR / "scan_upright" / comp_filename[1])
    vid_path = str(DATASET_DIR / "clips_video" / comp_filename[2])

    dataset.add_group_sample(
        components={
            "photo": ls.CreateImage(path=str(photo_path)),
            "scan_upright": ls.CreateImage(path=str(scan_path)),
            "clips_video": ls.CreateVideo(path=str(vid_path)),
        }
    )


# Enable when frontend is ready
ls.start_gui()
