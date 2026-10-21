# Wayve demo

Demo data for the Wayve call on 22 October 2026. The data is 50 dashcam clips from the
[Nexar Collision Prediction dataset](https://huggingface.co/datasets/nexar-ai/nexar_collision_prediction).
The Nexar Open Data License permits free use with attribution and prohibits resale.

## What the demo shows

A hand-built near-miss filter misses most near-misses in the dark. The GUI shows where the
filter is wrong. Search and example-based scoring find the clips that the filter missed.

The GUI stays up for the full demo. Each script connects to the same Postgres database,
changes tags, and stops. A browser refresh shows the change.

The database has two datasets:

- `nexar-clips`: 50 videos, with one embedding for each clip. The video frames have no
  embeddings.
- `nexar-frames`: one image for each second of each clip, 1,774 images. Each image has an
  embedding, YOLO boxes in the annotation source `yolo11n`, and frame metadata.

| Metadata key | Datasets | Content |
|---|---|---|
| `clip`, `light_conditions`, `weather`, `scene` | Both | Nexar labels |
| `near_miss` | Both | Nexar label. The ground truth for the filter. |
| `timestamp_s` | Frames | The second of the frame in its clip |
| `n_persons`, `n_vehicles`, `max_person_conf` | Frames | YOLO11n detections |
| `max_vehicle_area` | Frames | The largest vehicle box divided by the frame area |
| `seconds_to_event` | Frames | Near-miss clips only. Negative after the event. |

## Start and stop

Run all commands from `lightly_studio/` in the worktree. Use the venv of the worktree with
`env -u VIRTUAL_ENV`. The shell exports a `VIRTUAL_ENV` for a different checkout.

1. Start Postgres:

   ```bash
   docker start wayve-postgres
   ```

2. Start the GUI, and keep it open in its own terminal:

   ```bash
   env -u VIRTUAL_ENV ../.venv/bin/lightly-studio gui --db-url postgresql://lightly:lightly@localhost:5434/wayve --port 8021
   ```

3. Open `http://localhost:8021`. The GUI opens on `nexar-clips`.
4. To stop the GUI, push Ctrl+C.
5. To stop Postgres:

   ```bash
   docker stop wayve-postgres
   ```

If a script fails with a connection error, Postgres is not running. Do step 1 again.

## Scripts

Run each script in a second terminal while the GUI is up. Then refresh the browser.

| Command | Result |
|---|---|
| `env -u VIRTUAL_ENV ../.venv/bin/python src/lightly_studio/examples/wayve_demo/filter_v1.py` | Tags clips in `nexar-clips` with `filter_v1`, and prints the missed clips and the false positives. |
| `env -u VIRTUAL_ENV ../.venv/bin/python src/lightly_studio/examples/wayve_demo/frames_query.py` | Tags dark frames with a close vehicle in `nexar-frames` with `dark_close_vehicle`. |
| `env -u VIRTUAL_ENV ../.venv/bin/python src/lightly_studio/examples/wayve_demo/from_examples.py` | Tags the 50 frames most similar to the frames tagged `examples` with `from_examples`. |
| `env -u VIRTUAL_ENV ../.venv/bin/python src/lightly_studio/examples/wayve_demo/clear_tag.py clips filter_v1` | Removes one tag from all samples. Use `clips` or `frames`. |

Each script removes its tag first. Thus a second run gives the same result.

To show a "what if" change, edit `looks_like_near_miss` in `filter_v1.py`, or the query at
the top of `main()` in `frames_query.py`. Then run the script again.

Before you run `from_examples.py`, select 3 to 5 frames in `nexar-frames` and tag them
`examples`. Use dark frames from the missed clips. Without this tag, the script stops and
tells you to create it. To use a different tag or count, add
`--examples-tag <tag> --top <n>`.

## Reset

To remove one tag, run `clear_tag.py`.

To restore the full database to the state after the build:

1. Stop the GUI.
2. Restore the snapshot:

   ```bash
   docker exec -i wayve-postgres pg_restore --clean -U lightly -d wayve < ~/demo_data/wayve/wayve.clean.dump
   ```

3. Start the GUI again.

## Results of filter v1

The rule: a clip is a near-miss if a vehicle box fills 13% of the frame or more.

- The filter tags 20 clips. 13 clips are real near-misses, and 7 are false positives.
- The filter misses 13 of the 26 near-misses. 8 of these 13 clips are in the dark.
- All 7 false positives are clips in normal light.

Missed dark clips: `00093` (snow), `00108`, `00283`, `00317`, `00463`, `00763` (rain),
`00929`, `00936`.

## Where each feature works

| Feature | `nexar-clips` videos | Frames inside `nexar-clips` | `nexar-frames` |
|---|---|---|---|
| Text and image search | Yes | No | Yes |
| Embedding plot | Yes | No | Yes |
| Few-shot classifier | No | No | Yes |
| GUI query editor | No | No | Yes |
| Metadata filters, tags | Yes | Yes | Yes |

Use `nexar-frames` for all steps on frames.

## Build from zero

The build takes about 5 minutes on an Apple M5. It deletes all data in the database.

1. Request access to the Nexar dataset on Hugging Face. Approval is automatic.
2. Pick the clips. The script reads `meta_positive.csv` and `meta_negative.csv` from the
   `train/positive` and `train/negative` folders of the dataset:

   ```bash
   python3 src/lightly_studio/examples/wayve_demo/pick_clips.py
   ```

3. Download the clips in `selection.csv` to `~/demo_data/wayve/nexar/videos/`.
4. Download `yolo11n.pt` to `~/demo_data/wayve/`.
5. Create the Postgres container. Port 5433 is in use by a different local stack:

   ```bash
   docker run -d --name wayve-postgres --shm-size=1g -e POSTGRES_USER=lightly -e POSTGRES_PASSWORD=lightly -e POSTGRES_DB=wayve -p 5434:5432 pgvector/pgvector:0.8.1-pg18-bookworm
   ```

6. Build the datasets. The script also writes the frames to `~/demo_data/wayve/nexar/frames/`:

   ```bash
   env -u VIRTUAL_ENV ../.venv/bin/python src/lightly_studio/examples/wayve_demo/build_dataset.py
   ```

7. Save the snapshot for a reset:

   ```bash
   docker exec wayve-postgres pg_dump -U lightly -d wayve -Fc > ~/demo_data/wayve/wayve.clean.dump
   ```

To use a different database, set `WAYVE_DB_URL`. The scripts read it in `config.py`.
