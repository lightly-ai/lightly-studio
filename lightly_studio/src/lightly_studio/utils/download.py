"""Module for downloading example datasets from the web."""

import os
import shutil
import zipfile
from pathlib import Path

import requests
from tqdm import tqdm

# URL to download the main branch of the repo as a zip
ZIP_URL = "https://github.com/lightly-ai/dataset_examples/archive/refs/heads/main.zip"
# name of the folder inside the zip
REPO_DIR_IN_ZIP = "dataset_examples-main"


def download_example_dataset(target_dir: str = "dataset_examples", force: bool = False) -> str:
    """Downloads the lightly-ai/dataset_examples repository from GitHub.

    Args:
        target_dir:
            The directory where the dataset will be saved.
        force:
            If True, will download and overwrite existing data.
            If False, will skip download if target_dir exists.

    Returns:
        The path to the downloaded dataset directory.
    """
    target_path = Path(target_dir)

    # Check if data already exists
    if target_path.exists():
        if not force:
            print(
                f"'{target_path}' already exists. Skipping download. Use force=True to re-download."
            )
            return str(target_path)
        print(f"'{target_path}' exists. Forcing re-download...")
        shutil.rmtree(target_path)

    print(f"Downloading example dataset from GitHub to '{target_path}'...")

    # Download the zip file with a progress bar
    zip_path = Path(f"{target_dir}.zip")
    try:
        response = requests.get(ZIP_URL, stream=True)
        response.raise_for_status()

        # Get total file size from headers
        total_size = int(response.headers.get("content-length", 0))

        with open(zip_path, "wb") as f, tqdm(
            desc=f"Downloading {zip_path}",
            total=total_size,
            unit="iB",
            unit_scale=True,
            unit_divisor=1024,
        ) as bar:
            for chunk in response.iter_content(chunk_size=1024):
                size = f.write(chunk)
                bar.update(size)

        # Unzip the file
        print(f"Extracting '{zip_path}'...")
        temp_extract_dir = Path(f"{target_dir}_temp_extract")
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(temp_extract_dir)

        # Move the contents to the target directory
        shutil.move(str(temp_extract_dir / REPO_DIR_IN_ZIP), str(target_path))
        print(f"Successfully downloaded and extracted to '{target_path}'")

    finally:
        # Clean up temporary files
        if zip_path.exists():
            os.remove(zip_path)
        if temp_extract_dir.exists():
            shutil.rmtree(temp_extract_dir)

    return str(target_path)
