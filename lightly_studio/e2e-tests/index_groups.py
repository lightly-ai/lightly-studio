"""Example of how to add samples in coco format to a dataset."""

from pathlib import Path

import lightly_studio as ls
from lightly_studio.core.group.group_dataset import GroupDataset
from lightly_studio.core.image.create_image import CreateImage
from lightly_studio.core.video.create_video import CreateVideo
from lightly_studio.resolvers import collection_resolver, group_resolver

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
session = dataset.session

# Add samples to the dataset
# TODO: Switch away from resolvers
component_collections = collection_resolver.get_group_components(
    session=session,
    parent_collection_id=dataset.dataset_id,
)
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

    photo_id = CreateImage(path=photo_path).create_in_collection(
        session=session,
        collection_id=component_collections["photo"].collection_id,
    )
    scan_id = CreateImage(path=scan_path).create_in_collection(
        session=session,
        collection_id=component_collections["scan_upright"].collection_id,
    )
    vid_id = CreateVideo(path=vid_path).create_in_collection(
        session=session,
        collection_id=component_collections["clips_video"].collection_id,
    )

    group_resolver.create_many(
        session=session,
        collection_id=dataset.dataset_id,
        groups=[(photo_id, scan_id, vid_id)],
    )


# Optional: Print out the samples
for sample in dataset:
    print(f"Group sample ID: {sample.sample_id}")
    photo_comp = sample["photo"]
    scan_comp = sample["scan_upright"]
    vid_comp = sample["clips_video"]
    if photo_comp and scan_comp and vid_comp:
        print(
            f"Group components: {photo_comp.file_name}, {scan_comp.file_name}, "  # type: ignore[attr-defined]
            f"{vid_comp.file_name}"
        )

# Enable when frontend is ready
ls.start_gui()
