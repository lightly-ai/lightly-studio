# Wayve demo

Demo data for the Wayve call on 22 October 2026. The data is 50 dashcam clips from the
[Nexar Collision Prediction dataset](https://huggingface.co/datasets/nexar-ai/nexar_collision_prediction).
The Nexar Open Data License permits free use with attribution and prohibits resale.

## The story

A simple near-miss filter says: "a vehicle is close when its box fills 13% of the frame."
In the 2 seconds before each near-miss, this filter catches 7 of 52 frames. At night it
catches 1 of 24. LightlyStudio shows the gap, and example-based search finds the frames
that the filter misses.

## The data

The demo uses the dataset `nexar-frames`: one image for each second of each clip, 1,774
images. Each image has YOLO boxes and this metadata:

| Key | Content |
|---|---|
| `near_miss` | Nexar label. `true` if the clip ends in a collision or a near-collision. |
| `seconds_to_event` | Seconds until the event. Near-miss clips only. Negative after the event. |
| `light_conditions` | `Normal`, `Dark`, `Twilight` or `Bright` |
| `max_vehicle_area` | The largest vehicle box divided by the frame area. A large value means a close vehicle. |
| `clip`, `weather`, `scene`, `timestamp_s` | The clip, the conditions, and the second in the clip |
| `n_persons`, `n_vehicles`, `max_person_conf` | YOLO11n counts |

`near_miss` is a label for the full clip. Thus all frames of a near-miss clip have `true`,
also frames long before the event. Use `seconds_to_event` to get the frames near the event.

The dataset `nexar-clips` has the same 50 clips as videos.

## Before the call

1. Start the hosted stack. Run this command from the self-hosted worktree
   `/Users/gabrielfruet/dev/lightly/lightly-studio-self-hosted/.claude/worktrees/wayve-hosted`:

   ```bash
   docker compose -f docker-compose.yml -f docker-compose.wayve.yml up -d
   ```

2. Open `http://localhost:8200/workspace/login`. Sign in as `admin@example.com`. The
   password is `ADMIN_PASSWORD` in the `.env` file of the self-hosted worktree.
3. Open `nexar-frames` once, and wait until the images show. The first load takes about
   10 seconds.
4. Open a terminal for the scripts. Go to `lightly_studio/` in this worktree, and set the
   database URL of the hosted stack:

   ```bash
   cd /Users/gabrielfruet/dev/lightly/lightly-studio/.claude/worktrees/wayve-demo/lightly_studio
   export WAYVE_DB_URL="postgresql://lightly:$(grep '^POSTGRES_PASSWORD=' /Users/gabrielfruet/dev/lightly/lightly-studio-self-hosted/.claude/worktrees/wayve-hosted/.env | cut -d= -f2-)@localhost:5435/lightly_studio"
   ```

## During the call

### 1. Run the filter

```bash
env -u VIRTUAL_ENV ../.venv/bin/python src/lightly_studio/examples/wayve_demo/frames_query.py
```

The script tags 70 frames with `close_vehicle`. Refresh the browser. The tag shows in the
sidebar.

### 2. Show that the filter is wrong

Do these steps on `nexar-frames`, in the left sidebar. Read each count in the
**Showing N of 1,774 images** line at the bottom left.

1. Under **Metadata**, click **Add categorical metadata field**, then `near_miss`. Open
   **All values**, and tick `true`. The count is 828.
2. Scroll down to the **Seconds To Event** slider. Drag the right handle to about 2, then the
   left handle to about 0. The two handles are then almost on top of each other. The count
   is 52: the 2 seconds before each near-miss.
3. Tick the tag `close_vehicle`. The count is 7. The filter misses 45 of 52.
4. Add `light_conditions`, and tick `Dark`. The count is 1. Untick `close_vehicle`. The
   count is 24: dark frames with a vehicle close ahead.

Say: "In the 2 seconds before each near-miss, your filter catches 7 of 52 frames. At night
it catches 1 of 24."

### 3. Change the filter

The query is at the top of `frames_query.py`. For example, remove the `#` in front of the
`light_conditions` line. Then run the script again, and refresh the browser. Each run
removes the old `close_vehicle` tag first.

### 4. Find the missed frames from examples

1. Keep the filters of step 2: near-miss, dark, 0 to 2 seconds.
2. Select 3 to 5 frames that show a close vehicle.
3. Type `examples` in **Assign tag to selection**, and push Enter.
4. Run the script:

   ```bash
   env -u VIRTUAL_ENV ../.venv/bin/python src/lightly_studio/examples/wayve_demo/from_examples.py
   ```

5. Refresh the browser, clear the metadata filters, and tick `from_examples`. The 50 frames
   that look most like the examples show. Most of them are dark frames from near-miss clips.

If you tag a wrong frame, open the frame and click the **×** on the tag in the right panel.
If the `examples` tag does not exist, the script stops and tells you to create it.

## Reset

To remove a full tag, click **⋯** next to the tag in the sidebar, then **Delete**.

To restore the full database, run these commands from the self-hosted worktree:

```bash
docker compose -f docker-compose.yml -f docker-compose.wayve.yml stop studio
docker exec -i wayve-hosted-db-1 pg_restore --clean --no-owner -U lightly -d lightly_studio < ~/demo_data/wayve/wayve.clean.dump
docker compose -f docker-compose.yml -f docker-compose.wayve.yml start studio
```

## Backup GUI on port 8021

If the hosted stack fails, use the local GUI. It has its own copy of the data in the
container `wayve-postgres`.

1. Start Postgres:

   ```bash
   docker start wayve-postgres
   ```

2. Start the GUI from `lightly_studio/` in this worktree:

   ```bash
   env -u VIRTUAL_ENV ../.venv/bin/lightly-studio gui --db-url postgresql://lightly:lightly@localhost:5434/wayve --port 8021
   ```

3. In the terminal of the scripts, remove the hosted URL. The scripts then use the backup:

   ```bash
   unset WAYVE_DB_URL
   ```

To restore the backup database, stop the GUI, then run:

```bash
docker exec -i wayve-postgres pg_restore --clean -U lightly -d wayve < ~/demo_data/wayve/wayve.clean.dump
```

## About the hosted stack

The hosted stack is the compose project `wayve-hosted` in the self-hosted worktree, branch
`gabriel-wayve-hosted`. It has its own Postgres on port 5435, restored from
`~/demo_data/wayve/wayve.clean.dump`.

The released studio images (1.1.3 and older) do not know the schema of the demo database.
Thus the stack uses the image `lightly/lightly-studio-self-hosted:wayve-demo`, built for
arm64 from commit `0dd7af578` of this branch. The file `docker-compose.wayve.yml` selects it.

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
