"""Downloads short clips of GrandTour missions from Hugging Face and converts each to MCAP.

A full mission is 2 to 13 GB. A clip only needs a part of it:

- The small Zarr groups (`tf`, `anymal_state_odometry`, `hdr_*`) are downloaded in full.
- Of each lidar tar, only the first chunk of `points` (256 sweeps for the Hesai, 512 for
  the Livox), of `intensity`, `valid` and `timestamp` are fetched with HTTP range requests.
  The tar headers are read one by one to find the members.
- The image tars are streamed until the last frame of the clip, and only the frames in
  the clip are kept.

The lidars are the raw `hesai_points` and `livox_points`, as in the official GrandTour MCAP
files. Each clip then goes through `grand_tour_to_gt_box_mcap.py`, which writes the topics
of the official files, plus `hdr_left`, `hdr_right` and the transforms.

Each step skips the data that is already there, so a second run only fetches what a changed
clip window or a new group needs.

Usage:
    python download_grand_tour_clips.py <out_dir> [--count 20] [--start-seconds 10] [--seconds 10]
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tarfile
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import zarr

REPO_URL = "https://huggingface.co/datasets/leggedrobotics/grand_tour_dataset"
API_URL = "https://huggingface.co/api/datasets/leggedrobotics/grand_tour_dataset/tree/main"
# The lidars of the official files. The Hesai is first, as the converter expects.
CAMERAS = ["hdr_front", "hdr_left", "hdr_right"]
LIDARS = ["hesai_points", "livox_points"]
SMALL_GROUPS = ["tf", "anymal_state_odometry", *CAMERAS]
# The lidar members to fetch. `time`, `ring`, `tag` and `line` are per point and not needed.
LIDAR_MEMBER = re.compile(
    r"^[a-z_]+/(\.zattrs|\.zgroup|[a-z_]+/\.zarray|points/0\.0\.0|intensity/0\.0|valid/0\.0|timestamp/0|sequence_id/0)$"
)
_BLOCK = 512


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("out_dir", type=Path)
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--start-seconds", type=float, default=10.0)
    parser.add_argument("--seconds", type=float, default=10.0)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--missions", default=None, help="Comma-separated missions, instead of an even spread.")
    parser.add_argument("--mcap-dir", type=Path, default=None, help="Defaults to <out_dir>/mcap.")
    args = parser.parse_args()

    if args.missions:
        picks = args.missions.split(",")
    else:
        missions = _usable_missions()
        picks = [missions[int(i)] for i in np.linspace(0, len(missions) - 1, num=min(args.count, len(missions)))]
        print(f"{len(missions)} usable missions, picked {len(picks)}: {picks}")

    raw_dir = args.out_dir / "raw"
    mcap_dir = args.mcap_dir or args.out_dir / "mcap"

    def download(mission: str) -> str:
        try:
            _download_clip(
                mission=mission,
                mission_dir=raw_dir / mission,
                start_seconds=args.start_seconds,
                seconds=args.seconds,
            )
            return f"{mission}: downloaded"
        except Exception as error:  # noqa: BLE001
            return f"{mission}: FAILED {error!r}"

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for result in pool.map(download, picks):
            print(result, flush=True)

    converter = Path(__file__).with_name("grand_tour_to_gt_box_mcap.py")
    for mission in picks:
        if not (raw_dir / mission / "done").exists():
            continue
        output = mcap_dir / f"grand_tour_{mission}.mcap"
        if output.exists():
            continue
        subprocess.run(
            [
                sys.executable,
                "-I",
                str(converter),
                str(raw_dir / mission),
                str(output),
                "--start-seconds",
                str(args.start_seconds),
                "--max-seconds",
                str(args.seconds),
                "--cameras",
                ",".join(CAMERAS),
                "--hesai",
                LIDARS[0],
                "--livox",
                LIDARS[1],
                "--tf",
            ],
            check=False,
        )


def _usable_missions() -> list[str]:
    missions = sorted(e["path"] for e in _json(API_URL) if e["type"] == "directory")
    usable = []
    for mission in missions:
        try:
            data = {e["path"].rsplit("/", 1)[-1] for e in _json(f"{API_URL}/{mission}/data")}
            images = {e["path"].rsplit("/", 1)[-1] for e in _json(f"{API_URL}/{mission}/images")}
        except urllib.error.HTTPError:
            continue
        needed_data = {f"{name}.tar" for name in [*SMALL_GROUPS, *LIDARS]}
        if needed_data <= data and {f"{camera}.tar" for camera in CAMERAS} <= images:
            usable.append(mission)
    return usable


def _download_clip(mission: str, mission_dir: Path, start_seconds: float, seconds: float) -> None:
    data_dir = mission_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    base_url = f"{REPO_URL}/resolve/main/{mission}"
    # The root `.zgroup` of some missions is not valid JSON. It holds only the format.
    (data_dir / ".zgroup").write_text('{"zarr_format": 2}')

    for group in SMALL_GROUPS:
        if (data_dir / group / ".zattrs").exists():
            continue
        with urllib.request.urlopen(f"{base_url}/data/{group}.tar") as response:
            with tarfile.open(fileobj=response, mode="r|") as tar:
                tar.extractall(path=data_dir)

    for lidar in LIDARS:
        # `valid` is the last member of the tar, so it marks a complete fetch.
        if not (data_dir / lidar / "valid" / "0.0").exists():
            _fetch_tar_members(url=f"{base_url}/data/{lidar}.tar", pattern=LIDAR_MEMBER, dest=data_dir)

    # The window matches the one of `grand_tour_to_gt_box_mcap.py`.
    root = zarr.open_group(str(data_dir), mode="r")
    camera_stamps = {camera: root[camera]["timestamp"][:] for camera in CAMERAS}
    lidar_stamps = {lidar: root[lidar]["timestamp"][:] for lidar in LIDARS}
    start = max(stamps[0] for stamps in [*lidar_stamps.values(), *camera_stamps.values()]) + start_seconds
    end = start + seconds
    for lidar, stamps in lidar_stamps.items():
        rows = root[lidar]["points"].chunks[0]
        if np.searchsorted(stamps, end, side="right") > rows:
            raise ValueError(f"The clip ends after the first {rows} sweeps of {lidar}")

    for camera, stamps in camera_stamps.items():
        first = int(np.searchsorted(stamps, start))
        last = int(np.searchsorted(stamps, end, side="right")) - 1
        _stream_images(url=f"{base_url}/images/{camera}.tar", dest=mission_dir / "images", first=first, last=last)

    (mission_dir / "done").touch()


def _fetch_tar_members(url: str, pattern: re.Pattern[str], dest: Path) -> None:
    """Fetches the tar members whose names match `pattern`, without downloading the tar."""
    url = _resolve(url)
    offset = 0
    long_name: str | None = None
    while True:
        header = _get(url, start=offset, end=offset + _BLOCK - 1)
        if len(header) < _BLOCK or header == b"\0" * _BLOCK:
            return
        info = tarfile.TarInfo.frombuf(header, encoding="utf-8", errors="surrogateescape")
        data_offset = offset + _BLOCK
        offset = data_offset + -(-info.size // _BLOCK) * _BLOCK
        if info.type == tarfile.GNUTYPE_LONGNAME:
            long_name = _get(url, start=data_offset, end=data_offset + info.size - 1).rstrip(b"\0").decode()
            continue
        if info.type in (tarfile.XHDTYPE, tarfile.XGLTYPE):
            pax = _get(url, start=data_offset, end=data_offset + info.size - 1).decode()
            match = re.search(r"\d+ path=(.*)\n", pax)
            long_name = match.group(1) if match else None
            continue
        name = long_name or info.name
        long_name = None
        if info.isfile() and pattern.match(name):
            path = dest / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(_get(url, start=data_offset, end=data_offset + info.size - 1) if info.size else b"")


def _stream_images(url: str, dest: Path, first: int, last: int) -> None:
    """Streams an image tar and keeps the frames `first` to `last`, then stops."""
    folder = dest / Path(url).stem
    if all((folder / f"{index:06d}.jpeg").exists() for index in range(first, last + 1)):
        return
    with urllib.request.urlopen(url) as response:
        with tarfile.open(fileobj=response, mode="r|") as tar:
            for member in tar:
                if not member.isfile():
                    continue
                index = int(Path(member.name).stem)
                if index > last:
                    return
                if index >= first:
                    path = dest / member.name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    source = tar.extractfile(member)
                    assert source is not None
                    path.write_bytes(source.read())


def _resolve(url: str) -> str:
    """Returns the final URL after the Hugging Face redirect, so ranges skip the redirect."""
    request = urllib.request.Request(url, headers={"Range": "bytes=0-0"})
    with urllib.request.urlopen(request) as response:
        return response.geturl()


def _get(url: str, start: int | None = None, end: int | None = None) -> bytes:
    headers = {} if start is None else {"Range": f"bytes={start}-{end}"}
    for attempt in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=120) as response:
                return response.read()
        except OSError:
            if attempt == 4:
                raise
    raise AssertionError


def _json(url: str) -> list[dict]:
    return json.loads(_get(url))


if __name__ == "__main__":
    main()
