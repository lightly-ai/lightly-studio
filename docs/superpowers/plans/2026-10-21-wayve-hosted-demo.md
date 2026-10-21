# Wayve Demo on Hosted LightlyStudio Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

First action: start Docker Desktop if `docker ps` fails, then do Task 1. Total time is about 2 h, including two 5-minute builds.

**Goal:** Serve the Wayve demo data from LightlyStudio on a local Postgres, so the GUI stays up while small query scripts tag data in a second terminal.

**Architecture:** One Postgres container holds two datasets: `nexar-clips` (50 videos) and `nexar-frames` (the same clips at 1 fps as images). `lightly-studio gui --db-url ...` serves them. Each query script connects to the same URL, changes tags or metadata, and exits. The GUI shows the change after a browser refresh.

**Tech Stack:** LightlyStudio from origin/main (worktree venv, Python 3.9), Postgres with pgvector in Docker, ultralytics YOLO11n, OpenCV.

**Spec:** There is no separate spec. The decisions below come from a chat with the user on 2026-10-21 and are final.

## Context

The demo is a call with Wayve (autonomous driving) on 2026-10-22 at 14:00 CET. Their workflow is: run their own filter, look at the result in LightlyStudio, fix the filter, repeat. The story: a hand-built near-miss filter, based on YOLO vehicle box size, misses most near-misses in the dark. Search and example-based scoring find the clips it missed.

What exists today, on branch `gabriel-wayve-demo` (commit `215763399`, pushed). The worktree is:

```text
/Users/gabrielfruet/dev/lightly/lightly-studio/.claude/worktrees/wayve-demo
```

Its demo code is in `lightly_studio/src/lightly_studio/examples/wayve_demo/`:

- `pick_clips.py`: picks 50 Nexar clips into `selection.csv`. Keep it unchanged.
- `build_dataset.py`: builds a DuckDB file. Rewrite it in Task 2.
- `filter_v1.py`: the near-miss rule. It starts its own GUI. Rewrite it in Task 3.
- `README.md`: rewrite it in Task 5.

The data is in `~/demo_data/wayve/`. That folder holds `nexar/videos/` (50 clips, already downloaded), `nexar/selection.csv`, `nexar/meta_{positive,negative}.csv`, `yolo11n.pt`, and the old `wayve.db`, `wayve.clean.db` and `nexar/frames/`.

The user decided these points:

1. Hosted means a local Postgres, not a Lightly Enterprise instance, because the demo needs main's latest features.
2. The video dataset gets clip embeddings and clip metadata only, with no frame embeddings. The GUI Frames tab cannot search or plot frames anyway.
3. The frames dataset gets YOLO boxes, frame metadata and embeddings.
4. There are four query scripts: `filter_v1.py`, `frames_query.py`, `from_examples.py` and `clear_tag.py`.
5. Clean up the DuckDB setup, on the same worktree and branch.

## Global Constraints

- Run Python as `env -u VIRTUAL_ENV ../.venv/bin/python` from the worktree's `lightly_studio/` folder. The user's shell exports `VIRTUAL_ENV` for a different checkout. Plain `uv pip install` writes into that other venv.
- Use absolute paths, and `builtin cd` to change folders. Sibling worktrees and a zoxide `cd` shim can send relative paths to the wrong checkout.
- Postgres: container `wayve-postgres`, image `pgvector/pgvector:0.8.1-pg18-bookworm`, host port `5434`, user and password `lightly`, database `wayve`. Do not use port 5433, because another local stack holds it.
- Database URL: `postgresql://lightly:lightly@localhost:5434/wayve`. LightlyStudio adds the psycopg3 driver itself (`database/db_url.py:8`).
- GUI port: `8021`.
- Dataset names: `nexar-clips` and `nexar-frames`.
- Do not delete user data. Move old files to `~/demo_data/wayve/old-duckdb-2026-10-21/`.
- No unit tests. These are demo scripts, so you check each one by running it. Every script must pass `uv run ruff format`, `uv run ruff check` and `uv run mypy` on the `wayve_demo/` folder.
- Load the repo's `python-guide` skill before you edit Python. Import modules for functions and classes directly. Call functions with keyword arguments.
- Commits: `type: description`, 72 characters at most, ending with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Push to `origin gabriel-wayve-demo` after each task.

## Review Focus

1. **A script runs while the GUI is up.** It must not fail on a lock, and the GUI must show its tag after a refresh. Task 3 step 5 tests this.
2. **A script runs twice.** The second run must give the same tag counts, not double or stale ones. Task 3 and Task 4 each run their script twice.
3. **`from_examples.py` runs before you tag any examples.** It must stop with a clear message that names the tag to create in the GUI. It must not print a stack trace. Task 4 step 4 tests this.
4. **The GUI opens on the clips.** The root URL opens the newest root dataset (`lightly_studio_view/src/routes/+page.ts`). `build_dataset.py` must therefore create `nexar-frames` first and `nexar-clips` last. Task 2 step 4 checks this.
5. **Postgres is down.** The scripts fail with the connection error, and the README says how to start the container. No extra code is needed for this.

---

### Task 1: Clean up DuckDB and start Postgres

**Files:**
- Create: `lightly_studio/src/lightly_studio/examples/wayve_demo/config.py`
- Delete: the old DuckDB files, by moving them (step 1)

**Interfaces:**
- Produces, in `config.py`:
  - `DB_URL: str`, default `postgresql://lightly:lightly@localhost:5434/wayve`, overridable with the env var `WAYVE_DB_URL`
  - path constants `DATA_DIR`, `NEXAR_DIR`, `VIDEOS_DIR`, `FRAMES_DIR`, `YOLO_WEIGHTS`
  - name constants `CLIPS_DATASET = "nexar-clips"` and `FRAMES_DATASET = "nexar-frames"`
  - `def connect(cleanup_existing: bool = False) -> None`, which calls `db_manager.connect(db_url=DB_URL, cleanup_existing=cleanup_existing)`
- Other scripts import it as `from lightly_studio.examples.wayve_demo import config`. This is the same import pattern as `coco_plugins_demo/example_coco_plugins.py:26`.

- [ ] **Step 1: Move the old DuckDB files out of the way**

```bash
mkdir -p ~/demo_data/wayve/old-duckdb-2026-10-21
mv ~/demo_data/wayve/wayve.db ~/demo_data/wayve/wayve.clean.db ~/demo_data/wayve/nexar/frames ~/demo_data/wayve/old-duckdb-2026-10-21/
```

Expected: `ls ~/demo_data/wayve` shows `nexar`, `yolo11n.pt`, `build.log` and `old-duckdb-2026-10-21`.

- [ ] **Step 2: Start Postgres**

```bash
docker run -d --name wayve-postgres --shm-size=1g -e POSTGRES_USER=lightly -e POSTGRES_PASSWORD=lightly -e POSTGRES_DB=wayve -p 5434:5432 pgvector/pgvector:0.8.1-pg18-bookworm
```

Then wait until this command prints `1`:

```bash
docker exec -e PGPASSWORD=lightly wayve-postgres psql -h 127.0.0.1 -U lightly -d wayve -tAc 'SELECT 1'
```

Probe over TCP (`-h 127.0.0.1`), not the Unix socket. The bootstrap server answers on the socket before the real server accepts TCP (`lightly_studio/Makefile:180-185`).

- [ ] **Step 3: Write `config.py`** with the interface above, then run the lint and type checks.

- [ ] **Step 4: Check that the connection works**

```bash
env -u VIRTUAL_ENV ../.venv/bin/python -c "from lightly_studio.examples.wayve_demo import config; config.connect(); print('ok')"
```

Expected: `ok`. `connect()` creates the tables with `SQLModel.metadata.create_all` (`database/db_manager.py:333-359`).

- [ ] **Step 5: Commit** `chore: add Postgres config for the Wayve demo`

### Task 2: Build both datasets in Postgres

**Files:**
- Modify (rewrite): `lightly_studio/src/lightly_studio/examples/wayve_demo/build_dataset.py`

**Interfaces:**
- Consumes: `config.*` from Task 1.
- Produces the database contents that Tasks 3 and 4 read:
  - `nexar-frames`: one image per clip-second. The file name is `<clip stem>_<second:02d>.jpg`, for example `00054_07.jpg`. Metadata keys: `clip` (for example `00054.mp4`), `light_conditions`, `weather`, `scene`, `near_miss` (bool), `timestamp_s`, `n_persons`, `n_vehicles`, `max_person_conf`, `max_vehicle_area`, and `seconds_to_event` (near-miss clips only). The YOLO boxes are in annotation source `yolo11n`.
  - `nexar-clips`: 50 videos with metadata keys `clip`, `light_conditions`, `weather`, `scene` and `near_miss`.

- [ ] **Step 1: Change the frames step so that it does not depend on the video dataset**

Read each clip with `cv2.VideoCapture`. Keep frame index `round(s * fps)` for each whole second `s`, where `fps = CAP_PROP_FPS`. Write it as JPEG to `config.FRAMES_DIR`. Keep `_detect`, `Box`, `_set_clip_metadata` and `_set_frame_labels` from the current file. The YOLO and metadata logic does not change, only the frame source.

- [ ] **Step 2: Order the datasets.** `main()` must:
  1. call `config.connect(cleanup_existing=True)`
  2. create `nexar-frames` from `FRAMES_DIR` with `embed=True`, then set metadata and boxes
  3. create `nexar-clips` last, with `add_videos_from_path(path=config.VIDEOS_DIR, embed=True, embed_frames=False, target_fps=1)`, then set clip metadata

  Remove the old `VideoFrameSample` code paths.

- [ ] **Step 3: Run the build** (about 5 min)

```bash
env -u VIRTUAL_ENV ../.venv/bin/python src/lightly_studio/examples/wayve_demo/build_dataset.py
```

Expected: the output ends with `Done`, and `ls ~/demo_data/wayve/nexar/frames | wc -l` prints between 1774 and 1785. The clips are 14 to 41 s long, measured with `ffprobe`. The old build had 1,774 frames.

- [ ] **Step 4: Check the contents and the GUI landing page**

```bash
docker exec -e PGPASSWORD=lightly wayve-postgres psql -h 127.0.0.1 -U lightly -d wayve -c "select c.name, c.sample_type, count(distinct s.sample_id) samples, count(e.sample_id) embeddings from sample s join collection c using (collection_id) left join sample_embedding e using (sample_id) group by 1,2 order by 1"
```

Expected rows:
- `nexar-clips | VIDEO | 50 | 50`
- `nexar-frames | IMAGE | ~1780 | ~1780`
- `video_frame` with 0 embeddings
- `yolo11n` (ANNOTATION) with 0 embeddings

Check the table and column names against `models/` if the query fails. Then start the GUI as in Task 3 step 1, and open `http://localhost:8021`. Expected: it redirects to a `/video/` URL, that is, to `nexar-clips`.

- [ ] **Step 5: Save a reset snapshot**

```bash
docker exec wayve-postgres pg_dump -U lightly -d wayve -Fc > ~/demo_data/wayve/wayve.clean.dump
```

Expected: a file larger than 10 MB.

- [ ] **Step 6: Commit** `feat: build the Wayve demo datasets in Postgres`

### Task 3: Serve the GUI, and port filter_v1 and clear_tag

**Files:**
- Modify (rewrite): `lightly_studio/src/lightly_studio/examples/wayve_demo/filter_v1.py`
- Create: `lightly_studio/src/lightly_studio/examples/wayve_demo/clear_tag.py`
- Modify: `/Users/gabrielfruet/dev/lightly/lightly-studio/.claude/launch.json` (untracked, in the main checkout). Change the `wayve-demo` entry so that it runs the GUI command from step 1 on port 8021.

**Interfaces:**
- Consumes: `config.connect()`, and the frame metadata from Task 2.
- Produces:
  - `filter_v1.py`: tags clips in `nexar-clips` with `filter_v1`, prints the misses and false positives, and exits.
  - `clear_tag.py <clips|frames> <tag>`: removes the tag from every sample of that dataset and prints how many samples lost it.

- [ ] **Step 1: Start the GUI and leave it running**

```bash
env -u VIRTUAL_ENV ../.venv/bin/lightly-studio gui --db-url postgresql://lightly:lightly@localhost:5434/wayve --port 8021
```

The `--db-url` option is defined at `cli.py:159`.

- [ ] **Step 2: Rewrite `filter_v1.py`.**
  - Group the `nexar-frames` images by `metadata["clip"]`, sorted by `timestamp_s`.
  - Keep `looks_like_near_miss(clip, frames)` and `MIN_VEHICLE_AREA = 0.13` unchanged.
  - Tag the selected videos in `nexar-clips`. Remove the tag first, so that a second run gives the same result.
  - Print `missed (n): ...` and `false_positive (n): ...`.
  - Delete `_serve_clips`, `_wait_for_server` and every GUI start. The script only writes and exits.

- [ ] **Step 3: Write `clear_tag.py`.** It takes two positional args, read with `sys.argv`. Load the dataset, and call `sample.remove_tag(name=tag)` on each sample that has the tag.

- [ ] **Step 4: Run `filter_v1.py` twice** while the GUI is up.

Expected: both runs print the same two lists. With 1 fps frames from second 0, the counts can differ a little from the old result (13 missed, 5 false positives). Record the new counts for the README.

- [ ] **Step 5: Check concurrency.** In the browser, open the clips page and refresh it.

Expected: the `filter_v1` tag is in the sidebar. Ticking it shows the same number of clips that the script tagged. If the GUI does not show the tag after a refresh, stop and report it. Do not work around it. The point of this setup is that the server keeps running.

- [ ] **Step 6: Run `clear_tag.py clips filter_v1`**, then refresh the GUI.

Expected: the tag shows 0 clips. Then run `filter_v1.py` again to restore it.

- [ ] **Step 7: Commit** `feat: run Wayve query scripts against the hosted GUI`

### Task 4: frames_query and from_examples

**Files:**
- Create: `lightly_studio/src/lightly_studio/examples/wayve_demo/frames_query.py`
- Create: `lightly_studio/src/lightly_studio/examples/wayve_demo/from_examples.py`

**Interfaces:**
- Consumes: `config.connect()`, and the frame metadata from Task 2.
- Produces:
  - `frames_query.py`: tags `nexar-frames` images with `dark_close_vehicle`.
  - `from_examples.py [--examples-tag examples] [--top 50]`: tags the top N frames with `from_examples`.

- [ ] **Step 1: Write `frames_query.py`.** Clear the `dark_close_vehicle` tag first, as in `clear_tag.py`. Then run this query and print the count:

```python
dataset.query().match(AND(
    ImageSampleField.metadata["light_conditions"] == "Dark",
    ImageSampleField.metadata["max_vehicle_area"] >= 0.13,
)).add_tag("dark_close_vehicle")
```

The query is the part the user edits live, so keep it at the top of `main()`.

- [ ] **Step 2: Run it twice.** Expected: both runs print the same count, greater than 0. The GUI shows the tag on `nexar-frames` after a refresh.

- [ ] **Step 3: Write `from_examples.py`.**
  1. Call `dataset.compute_similarity_metadata(query_tag_name=examples_tag, metadata_name="similarity_examples")` (`core/dataset.py:169`).
  2. Clear `from_examples`.
  3. Run `dataset.query().order_by(OrderByMetadataField("similarity_examples").desc()).slice(limit=top).add_tag("from_examples")`. `desc()` is defined at `core/dataset_query/order_by.py:139`.

  Use `argparse` for the two options.

- [ ] **Step 4: Run it without an `examples` tag.** Expected: it exits with code 1 and prints one line: `Tag 'examples' not found on nexar-frames. Select 3-5 frames in the GUI and tag them 'examples'.`. There must be no traceback. `compute_similarity_metadata` raises `ValueError("Query tag not found")`, so catch exactly that.

- [ ] **Step 5: Run it with examples.** In the GUI, tag 3 dark frames from missed near-miss clips as `examples`. Run the script twice. Expected: both runs tag 50 frames. In the GUI, `from_examples` mostly shows dark frames with a close vehicle.

- [ ] **Step 6: Commit** `feat: add frame query and example-based scoring scripts`

### Task 5: README, final check and memory

**Files:**
- Modify (rewrite): `lightly_studio/src/lightly_studio/examples/wayve_demo/README.md`
- Modify: `/Users/gabrielfruet/.claude/projects/-Users-gabrielfruet-dev-lightly-lightly-studio/memory/wayve-demo.md`

- [ ] **Step 1: Rewrite the README** in Simplified Technical English (the user's `simple-english` skill). Cover these sections and nothing else:
  1. what the demo shows
  2. start and stop Postgres and the GUI
  3. the four scripts, each with one command and one line on what it tags
  4. reset: `clear_tag.py` for one tag, or a full restore with the GUI stopped:

     ```bash
     docker exec -i wayve-postgres pg_restore --clean -U lightly -d wayve < ~/demo_data/wayve/wayve.clean.dump
     ```
  5. the new `filter_v1` counts from Task 3
  6. the feature table: search, plot, few-shot classifier and the GUI query editor work on `nexar-frames`. Clips support search and the plot only. Frames inside clips have neither.
  7. building from zero

- [ ] **Step 2: Do a dry run from a clean state.** Restore the dump, start the GUI, then run `filter_v1.py`, `frames_query.py` and `from_examples.py` in order. Expected: each tag appears in the GUI after a refresh, and the GUI never restarts.

- [ ] **Step 3: Update the memory file.** Replace the DuckDB lines with:
  - the Postgres container, port and URL
  - the GUI command
  - the dump path
  - "frames and clips are separate datasets; video frames have no embeddings"

  Keep the lines on the VIRTUAL_ENV trap and the GUI gaps.

- [ ] **Step 4: Commit and push** `docs: rewrite the Wayve demo README for the hosted setup`
