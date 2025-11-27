"""Module for downloading example datasets from the web."""

import logging
import os
import shutil
import zipfile
from pathlib import Path

import requests
from tqdm import tqdm

from lightly_studio.type_definitions import PathLike

logger = logging.getLogger(__name__)

# URL to download the main branch of the repo as a zip
ZIP_URL = "https://github.com/lightly-ai/dataset_examples/archive/refs/heads/main.zip"
# name of the folder inside the zip
REPO_DIR_IN_ZIP = "dataset_examples-main"


def download_example_dataset(
    download_dir: PathLike = "dataset_examples", force_redownload: bool = False
) -> str:
    """Downloads the lightly-ai/dataset_examples repository from GitHub.

    Args:
        download_dir:
            The directory where the dataset will be saved.
        force_redownload:
            If True, will download and overwrite existing data.
            If False, will skip download if target_dir exists.

    Returns:
        The path to the downloaded dataset directory.
    """
    # Convert the user-provided path to an absolute, standard path.
    # This handles '~' (home) and relative paths (../).
    target_path = Path(download_dir).expanduser().resolve()
    zip_path = target_path.with_name(f"{target_path.name}.zip")
    temp_extract_dir = target_path.with_name(f"{target_path.name}_temp_extract")

    # Check if data already exists.
    if target_path.exists():
        if not force_redownload:
            logger.info(
                f"'{target_path}' already exists. Skipping download. "
                "Use force_redownload=True to re-download."
            )
            return str(target_path)
        logger.info(f"'{target_path}' exists. Forcing re-download...")

    logger.info(f"Downloading example dataset from GitHub to '{target_path}'...")

    # Ensure parent folders exist.
    target_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with requests.get(url=ZIP_URL, stream=True, timeout=30) as response:
            response.raise_for_status()

            total_size = int(response.headers.get("content-length", 0))

            with open(file=zip_path, mode="wb") as f, tqdm(
                desc=f"Downloading {zip_path}",
                total=total_size,
                unit="iB",
                unit_scale=True,
                unit_divisor=1024,
            ) as bar:
                for chunk in response.iter_content(chunk_size=1024):
                    size = f.write(chunk)
                    bar.update(n=size)

        logger.info(f"Extracting '{zip_path}'...")
        with zipfile.ZipFile(file=zip_path, mode="r") as z:
            z.extractall(path=temp_extract_dir)

        # Delete the old data only after*the new data is fully downloaded and extracted.
        if target_path.exists():
            shutil.rmtree(path=target_path)

        # Move the contents to the target directory.
        shutil.move(src=str(temp_extract_dir / REPO_DIR_IN_ZIP), dst=str(target_path))
        logger.info(f"Successfully downloaded and extracted to '{target_path}'")

    finally:
        # Clean up temporary files.
        if zip_path.exists():
            os.remove(path=zip_path)
        if temp_extract_dir.exists():
            shutil.rmtree(path=temp_extract_dir)

    return str(target_path)
