# Wayve demo

Demo data for the Wayve call on 22 October 2026. The data is 50 dashcam clips from the
[Nexar Collision Prediction dataset](https://huggingface.co/datasets/nexar-ai/nexar_collision_prediction).
The Nexar Open Data License permits free use with attribution and prohibits resale.

The story of the demo: a hand-built near-miss filter misses most near-misses in the dark.
The GUI shows where the filter is wrong. Search and the few-shot classifier find the clips
that the filter missed.

## Files

| Path | Content |
|---|---|
| `~/demo_data/wayve/wayve.db` | The demo database. |
| `~/demo_data/wayve/wayve.clean.db` | A copy of the database, for a reset. |
| `~/demo_data/wayve/nexar/videos/` | The 50 clips, about 700 MB. |
| `~/demo_data/wayve/nexar/frames/` | 1,774 frames at 1 fps, as JPEG files. |
| `~/demo_data/wayve/nexar/selection.csv` | The clips and their Nexar labels. |

The database has two datasets:

- `nexar-clips`: 50 videos. Each video has one embedding, and each frame has one embedding.
- `nexar-frames`: the same 1,774 frames as images.

## Metadata

| Key | Level | Source |
|---|---|---|
| `light_conditions`, `weather`, `scene` | Clip | Nexar labels |
| `near_miss` | Clip | Nexar label. Ground truth for the filter. |
| `n_persons`, `n_vehicles`, `max_person_conf` | Frame | YOLO11n |
| `max_vehicle_area` | Frame | The largest vehicle box divided by the frame area |
| `seconds_to_event` | Frame | Near-miss clips only. Negative after the event. |

The YOLO boxes are in the annotation source `yolo11n`.

## Run the demo

Run the commands from `lightly_studio/` in the worktree.

1. Run the filter:

   ```bash
   env -u VIRTUAL_ENV ../.venv/bin/python src/lightly_studio/examples/wayve_demo/filter_v1.py
   ```

2. Read the `missed` and `false_positive` lists in the output.
3. Open the `Clips:` URL from the output. The script also opens it in the browser.
4. To stop the GUI, push Ctrl+C.

The filter is `looks_like_near_miss` in `filter_v1.py`. To show a "what if" change,
edit this function, stop the GUI, and run the script again.

## Reset after a dry run

Stop the GUI before you copy the file:

```bash
cp ~/demo_data/wayve/wayve.clean.db ~/demo_data/wayve/wayve.db
```

## Results of filter v1

The rule: a clip is a near-miss if a vehicle box fills 13% of the frame or more.

- The filter tags 18 clips. 13 clips are real near-misses, and 5 are false positives.
- The filter misses 13 of the 26 near-misses. 8 of these 13 clips are in the dark.
- All 5 false positives are daylight clips.

Missed dark clips: `00093` (snow), `00108`, `00283`, `00317`, `00463`, `00763` (rain),
`00929`, `00936`.

## Where each feature works

| Feature | `nexar-clips` Videos | `nexar-clips` Frames | `nexar-frames` |
|---|---|---|---|
| Text and image search | Yes | No | Yes |
| Embedding plot | Yes | No | Yes |
| Few-shot classifier | No | No | Yes |
| GUI query editor | No | No | Yes |
| Metadata filters, tags | Yes | Yes | Yes |

The frames have embeddings in the database, but the Frames view does not show search or
the plot. Use `nexar-frames` for all frame-level steps.

## Build from zero

The build takes about 5 minutes on an Apple M5.

1. Request access to the Nexar dataset on Hugging Face. Approval is automatic.
2. Pick the clips. The script reads `meta_positive.csv` and `meta_negative.csv` from the
   `train/positive` and `train/negative` folders of the dataset:

   ```bash
   python3 src/lightly_studio/examples/wayve_demo/pick_clips.py
   ```

3. Download the clips in `selection.csv` to `~/demo_data/wayve/nexar/videos/`.
4. Download `yolo11n.pt` to `~/demo_data/wayve/`.
5. Build the database:

   ```bash
   env -u VIRTUAL_ENV ../.venv/bin/python src/lightly_studio/examples/wayve_demo/build_dataset.py
   ```

The GUI root URL opens the newest dataset, which is `nexar-frames`. DuckDB cannot change
the creation time of a dataset, so `filter_v1.py` opens the clips URL instead.
