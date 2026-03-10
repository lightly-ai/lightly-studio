"""Index a group dataset with image and video components."""

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import lightly_studio as ls
from lightly_studio.core.group.group_dataset import GroupDataset

DATA_DIR = Path("datasets/midv_2020_10_samples")


def collect_group_samples(
    base_dir: str,
    photo_subdir: str,
    scan_subdir: str,
    video_subdir: str,
    image_extension: str = ".jpg",
    video_extension: str = ".mp4",
    verbose: bool = False,
) -> List[Dict[str, Any]]:
    """This function collects and returns all group samples from a dataset directory.

    It walks through the photo subdirectory, and for each photo it finds,
    it looks for the corresponding scan and video files. It then returns
    a list of dictionaries, where each dictionary contains the component
    name mapped to the file path string.

    Args:
        base_dir: The base directory path as a string.
        photo_subdir: The name of the photo subdirectory.
        scan_subdir: The name of the scan subdirectory.
        video_subdir: The name of the video subdirectory.
        image_extension: The file extension for image files.
        video_extension: The file extension for video files.
        verbose: Whether to print debug information.

    Returns:
        A list of dictionaries containing component names and paths.
    """
    result_list = []
    base_path = Path(base_dir)
    photo_dir_path = base_path / photo_subdir
    # Check if the directory exists
    if os.path.exists(str(photo_dir_path)) == False:
        print("Error: directory " + str(photo_dir_path) + " does not exist!")
        return []
    all_photo_files = list(photo_dir_path.glob("*" + image_extension))
    all_photo_files = sorted(all_photo_files)
    count = 0
    for i in range(len(all_photo_files)):
        photo_file = all_photo_files[i]
        file_name = photo_file.name
        stem = photo_file.stem
        scan_file = base_path / scan_subdir / file_name
        video_file_name = stem + video_extension
        video_file = base_path / video_subdir / video_file_name
        # Check that scan file exists
        if os.path.exists(str(scan_file)) == True:
            pass
        else:
            if verbose:
                print("Warning: scan file not found: " + str(scan_file))
            continue
        # Check that video file exists
        if os.path.exists(str(video_file)) == True:
            pass
        else:
            if verbose:
                print("Warning: video file not found: " + str(video_file))
            continue
        sample_dict = {}
        sample_dict["photo"] = str(photo_file)
        sample_dict["scan"] = str(scan_file)
        sample_dict["video"] = str(video_file)
        count = count + 1
        result_list.append(sample_dict)
    if verbose:
        print("Found " + str(count) + " complete group samples")
    return result_list


# Clean up existing database
ls.db_manager.connect(cleanup_existing=True)

# Define group components
group_dataset = GroupDataset.create(
    components=[
        ("photo", ls.SampleType.IMAGE),
        ("scan_upright", ls.SampleType.IMAGE),
        ("clip_video", ls.SampleType.VIDEO),
    ]
)

# Add samples to group dataset
samples = collect_group_samples(
    base_dir=str(DATA_DIR),
    photo_subdir="photo",
    scan_subdir="scan_upright",
    video_subdir="clip_video",
    verbose=True,
)
for sample in samples:
    group_dataset.add_group_sample(
        components={
            "photo": ls.CreateImage(path=sample["photo"]),
            "scan_upright": ls.CreateImage(path=sample["scan"]),
            "clip_video": ls.CreateVideo(path=sample["video"]),
        }
    )

ls.start_gui()
