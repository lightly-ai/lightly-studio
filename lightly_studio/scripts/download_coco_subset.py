#!/usr/bin/env python3
"""
Build a random N-image subset of COCO train2017 (images + matching annotations),
in the same layout as dataset_examples/coco_subset_128_images:

    <output-dir>/
        images/*.jpg
        instances_train2017.json   (filtered to sampled images only)
        captions_train2017.json    (filtered to sampled images only)
        README.md

Run this on a machine with real internet access and enough disk space
(~15-19 GB for 100,000 images + ~250 MB for the annotations zip).

Usage:
    pip install requests tqdm
    python download_coco_subset.py --num-images 100000 --output-dir ./coco_subset_100k_images

Re-running with the same --seed resumes safely: already-downloaded images are skipped,
and the annotations zip is cached locally so it isn't re-downloaded.
"""

import argparse
import json
import os
import random
import sys
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, **kwargs):
        return iterable

ANNOTATIONS_ZIP_URL = "http://images.cocodataset.org/annotations/annotations_trainval2017.zip"
IMAGE_BASE_URL = "http://images.cocodataset.org/train2017"


def download_file(url: str, dest: Path, chunk_size: int = 1 << 20) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        with open(tmp, "wb") as f, tqdm(
            total=total, unit="B", unit_scale=True, desc=dest.name
        ) as bar:
            for chunk in r.iter_content(chunk_size=chunk_size):
                f.write(chunk)
                bar.update(len(chunk))
    tmp.rename(dest)


def ensure_annotations(cache_dir: Path) -> tuple[Path, Path]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    zip_path = cache_dir / "annotations_trainval2017.zip"
    instances_path = cache_dir / "annotations" / "instances_train2017.json"
    captions_path = cache_dir / "annotations" / "captions_train2017.json"

    if instances_path.exists() and captions_path.exists():
        return instances_path, captions_path

    if not zip_path.exists():
        print("Downloading COCO train2017 annotations (~241 MB)...")
        download_file(ANNOTATIONS_ZIP_URL, zip_path)

    print("Extracting instances_train2017.json and captions_train2017.json...")
    with zipfile.ZipFile(zip_path) as zf:
        for name in ("annotations/instances_train2017.json", "annotations/captions_train2017.json"):
            zf.extract(name, cache_dir)

    return instances_path, captions_path


def download_one(args):
    file_name, dest_dir = args
    dest = dest_dir / file_name
    if dest.exists() and dest.stat().st_size > 0:
        return True, file_name
    url = f"{IMAGE_BASE_URL}/{file_name}"
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        tmp = dest.with_suffix(dest.suffix + ".part")
        with open(tmp, "wb") as f:
            f.write(r.content)
        tmp.rename(dest)
        return True, file_name
    except Exception as e:
        return False, f"{file_name}: {e}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--num-images", type=int, default=100_000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--output-dir", type=str, default="./coco_subset_100k_images")
    ap.add_argument("--cache-dir", type=str, default="./_coco_cache")
    ap.add_argument("--workers", type=int, default=32)
    ap.add_argument("--skip-captions", action="store_true", help="Don't filter/write captions_train2017.json")
    args = ap.parse_args()

    out_dir = Path(args.output_dir)
    images_dir = out_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = Path(args.cache_dir)

    instances_path, captions_path = ensure_annotations(cache_dir)

    print("Loading instances_train2017.json...")
    with open(instances_path) as f:
        instances = json.load(f)

    all_images = instances["images"]
    total_available = len(all_images)
    n = min(args.num_images, total_available)
    if args.num_images > total_available:
        print(f"Warning: requested {args.num_images}, but train2017 only has {total_available} images. Using {n}.")

    random.seed(args.seed)
    sampled_images = random.sample(all_images, n)
    sampled_ids = {img["id"] for img in sampled_images}
    print(f"Sampled {len(sampled_images)} images (seed={args.seed}).")

    # Filter instances annotations to sampled images only
    filtered_instances = dict(instances)
    filtered_instances["images"] = sampled_images
    filtered_instances["annotations"] = [
        a for a in instances["annotations"] if a["image_id"] in sampled_ids
    ]
    with open(out_dir / "instances_train2017.json", "w") as f:
        json.dump(filtered_instances, f)
    print(f"Wrote instances_train2017.json ({len(filtered_instances['annotations'])} annotations).")

    if not args.skip_captions:
        print("Loading captions_train2017.json...")
        with open(captions_path) as f:
            captions = json.load(f)
        filtered_captions = dict(captions)
        filtered_captions["images"] = sampled_images
        filtered_captions["annotations"] = [
            a for a in captions["annotations"] if a["image_id"] in sampled_ids
        ]
        with open(out_dir / "captions_train2017.json", "w") as f:
            json.dump(filtered_captions, f)
        print(f"Wrote captions_train2017.json ({len(filtered_captions['annotations'])} annotations).")

    # Download images
    print(f"Downloading {len(sampled_images)} images with {args.workers} workers...")
    jobs = [(img["file_name"], images_dir) for img in sampled_images]
    failures = []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = [ex.submit(download_one, job) for job in jobs]
        for fut in tqdm(as_completed(futures), total=len(futures), desc="images"):
            ok, info = fut.result()
            if not ok:
                failures.append(info)

    if failures:
        fail_path = out_dir / "failed_downloads.txt"
        with open(fail_path, "w") as f:
            f.write("\n".join(failures))
        print(f"{len(failures)} images failed to download. See {fail_path}. Re-run the same command to retry only missing files.")
    else:
        print("All images downloaded successfully.")

    readme = out_dir / "README.md"
    readme.write_text(
        f"This is a random subset of {len(sampled_images)} images "
        f"(seed={args.seed}) of the COCO 2017 Train dataset "
        f"(https://cocodataset.org/#download).\n"
        f"It contains object detections, instance segmentations"
        + ("" if args.skip_captions else ", and captions") + ".\n"
    )
    print(f"Done. Subset written to {out_dir}/")


if __name__ == "__main__":
    main()
