"""Example of how to create a group dataset."""

from pathlib import Path

from environs import Env, EnvError

import lightly_studio as ls

# Read environment variables
env = Env()
env.read_env()

# Set the path to the dataset directory
try:
    dataset_path = env.path("EXAMPLES_MIDV_PATH")
except EnvError as e:
    raise EnvError(
        "EXAMPLES_MIDV_PATH is not set. In lightly_studio/, clone the example "
        "dataset (`git clone https://github.com/lightly-ai/dataset_examples`), then "
        "run `cp .env.example .env` and set EXAMPLES_MIDV_PATH (see CONTRIBUTING.md)."
    ) from e

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

# Start GUI
ls.start_gui()
