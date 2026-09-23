# Camera demo: from a camera feed to a deployed detector

This demo runs the full loop of a camera application on one machine:

1. Watch a camera feed (RTSP, webcam, or video file).
2. Bookmark interesting frames. Each frame becomes an image sample in LightlyStudio.
3. Review the frames in the LightlyStudio grid and group them with tags.
4. Draw bounding boxes with the LightlyStudio annotation tools.
5. Train a detector with LightlyTrain from the "Plugins" menu, then read the metrics.
6. Deploy the model on the same feed and send the detections to MQTT or a Python script.

Steps 3, 4 and 5 are LightlyStudio and LightlyTrain without changes. Steps 1, 2 and 6 are
this example: one page named Camera Station, plus five operators (plugins).

## What is new and what is native

| Step | Component | New code |
|---|---|---|
| Camera feed, bookmark | Camera Station page on port 8002 | `camera.py`, `station.py`, `station.html` |
| Grid, tags, labeling | LightlyStudio | none |
| Train, stats | "Train object detector" operator plus LightlyTrain | `operators.py`, `training.py`, `train_worker.py` |
| Model review | LightlyStudio evaluation runs | `dataset_bridge.py` writes the predictions |
| Deploy, signals | Live detector plus MQTT and script hooks | `deployment.py`, `integrations.py` |

The new code is about 1,500 lines. It adds no route and no component to LightlyStudio
itself.

## Installation

The demo needs Python 3.10 or later, LightlyStudio, and LightlyTrain.

```bash
pip install lightly-studio lightly-train paho-mqtt
```

## Run the demo

Start the demo with a webcam:

```bash
python -m lightly_studio.examples.camera_plugins_demo.run_camera_demo --source 0
```

Start the demo with an RTSP camera and MQTT:

```bash
python -m lightly_studio.examples.camera_plugins_demo.run_camera_demo \
    --source rtsp://user:password@192.168.1.64:554/Streaming/Channels/101 \
    --mqtt-host localhost \
    --hook-script src/lightly_studio/examples/camera_plugins_demo/example_hook.py
```

Two pages open:

- Camera Station: http://localhost:8002
- LightlyStudio: http://localhost:8001

Main options:

| Option | Default | Function |
|---|---|---|
| `--source` | `0` | RTSP or HTTP URL, webcam index, or video file. A file plays in a loop. |
| `--data-dir` | `camera_demo_data` | Holds the database, the frames, and the training runs. |
| `--mqtt-host` | none | MQTT broker. MQTT is off when this option is not set. |
| `--hook-script` | none | Python file with `on_detections` and `on_event` functions. |
| `--model` | `ltdetrv2-s-coco` | LightlyTrain model that training starts from. |
| `--steps` | `40` | Training steps. |
| `--embed` | off | Embed each frame, for similarity search in LightlyStudio. |
| `--reset` | off | Delete the database before the start. |

### Simulate an RTSP camera

If there is no camera, serve a video file as an RTSP stream:

```bash
brew install mediamtx ffmpeg
./simulate_rtsp_camera.sh my_video.mp4
```

The stream is then at `rtsp://127.0.0.1:8554/cam`.

To serve a folder of videos as one camera each, use the other script:

```bash
./simulate_rtsp_cameras.sh ~/demo_data/cameras
```

A file named `pool.mp4` becomes `rtsp://127.0.0.1:8554/pool`. Type another URL in the
source field of the Camera Station to change camera while the demo runs.

### Example camera feeds

Any video file works. These five scenes come from the example datasets and cover
different object types:

| Feed | Scene | Classes to label |
|---|---|---|
| `pool.mp4` | Fixed camera on a pool, two water polo players | player, ball |
| `workbench.mp4` | Workshop bench, a person cleans and polishes shoes | shoe, hand, spray can |
| `documents.mp4` | Desk with identity documents, one after the other | id card, passport |
| `kitchen.mp4` | Kitchen counter during food preparation | hand, pot, vegetable |
| `traffic.mp4` | Street scenes from traffic cameras | car, truck, person |

`pool.mp4` is the easiest first demo: the camera does not move, the two classes are
clear, and 20 labeled frames are enough.

NOTE: `traffic.mp4` is built from single images, so the scene changes every 1.5
seconds. The other four feeds are continuous video.

## Demo script

1. Open the Camera Station. The live feed plays.
2. Click **Bookmark frame**, or press the space bar, on 20 to 40 interesting frames. The
   counter shows how many frames the dataset holds.
3. Open LightlyStudio. The frames are in the grid, with the tag `bookmarked`.
4. Select frames and assign a tag, for example `line-a`. This tag is the "project".
5. Double-click a frame. Press `e` for edit mode, then `b` for the bounding box tool.
   Draw a box and give it a class name. Press the right arrow key for the next frame.
6. Go back to the grid. Open **Menu > Plugins > Train object detector (LightlyTrain)**.
   Set the steps, then run it. The operator returns immediately.
7. Watch the progress in the Models panel of the Camera Station. A run of 40 steps takes
   4 to 8 minutes on a laptop CPU.
8. When the run is complete, the demo predicts on the validation split and creates an
   evaluation run in LightlyStudio. Open the **Eval** tab to see the confusion matrix,
   the training settings, and the LightlyTrain metrics. Click a cell of the matrix to
   filter the grid to those images.
9. Open **Menu > Plugins > Deploy model to camera**, or click **Deploy** on the Camera
   Station. The live feed then shows the boxes of the model.
10. Watch the MQTT messages in a second terminal:

    ```bash
    python -m lightly_studio.examples.camera_plugins_demo.mqtt_listener --host localhost
    ```

11. Set **auto-bookmark low-confidence frames**. The demo then collects the frames that
    the model is unsure about, with the tag `low-confidence`. These frames are the next
    labeling batch.

## The five operators

| Operator | Function |
|---|---|
| Train object detector (LightlyTrain) | Exports the annotations of the current view and starts a training run. |
| Training status | Reports the progress and the metrics of the runs. |
| Deploy model to camera | Runs a model on the live feed. |
| Stop camera deployment | Takes the model off the feed. |
| Bookmark current camera frame | Saves the current frame, from inside LightlyStudio. |

Operators run inside the HTTP request, and the LightlyStudio interface is blocked while
one runs. For this reason the training operator starts a subprocess and returns after
about 0.2 seconds.

## Integrations

Each inference result goes to the integrations dispatcher. Two messages leave the demo:

- `lightly/camera/detections` holds every current detection, at most once per second.
- `lightly/camera/events` holds one message per class whose object count changed.

A new object count must hold for one second before it counts as a change. Without this
delay, a detector that flickers sends an event on every frame.

The Python script hook receives the same messages. `example_hook.py` shows the pattern:
it writes a CSV row and returns a text line for the event log of the Camera Station.

```python
def on_event(message: dict) -> str | None:
    if message["class"] == "person" and message["current"] > message["previous"]:
        return "ALERT: person in view -> stop signal sent"
    return None
```

## How the parts fit together

The camera reader, the LightlyStudio server, the Camera Station server and the live
model share one process. DuckDB accepts one process at a time, so a second process
cannot open the same database. Training is the exception: it runs as a subprocess,
because it needs no database.

```text
                        one process
  +-------------------------------------------------------------+
  |  camera thread  -->  frame  -->  station (port 8002)         |
  |                        |            bookmark, MJPEG stream   |
  |                        v                                     |
  |                  live detector  -->  MQTT, Python script     |
  |                                                              |
  |  LightlyStudio server (port 8001) + 5 operators              |
  +-------------------------------------------------------------+
                               |
                               v  subprocess
                        LightlyTrain training
```

Frames are written to `<data-dir>/bookmarks/`. LightlyStudio reads images from their
file path, so these files must stay there.

## Measurements on an M-series MacBook Pro

| Action | Result |
|---|---|
| RTSP feed at 960x540 | 26 frames per second |
| Training, `ltdetrv2-s-coco`, 26 images, 60 steps, 448 px, CPU | 7.9 minutes |
| Live inference, `ltdetrv2-s-coco`, MPS | 19 ms per frame (53 frames per second) |
| Live inference, CPU | 45 ms per frame (22 frames per second) |

CAUTION: The backward pass of LT-DETR fails on MPS with `mat2 must be a matrix`.
Training uses the CPU on Apple silicon. Inference uses MPS.

## Known limits

- Operators give no progress. The Camera Station page shows the training progress
  instead, from the LightlyTrain log file.
- The LightlyStudio grid does not refresh by itself. New frames appear after a reload,
  after an operator runs, or when the browser tab gets the focus again.
- The demo trains on the images that have annotations in the source `annotation`. It
  skips images without annotations and reports how many.
- The evaluation run computes precision, recall and the confusion matrix. LightlyStudio
  does not compute mAP. The mAP of LightlyTrain is in the configuration of the run.
- The auto schedule of LT-DETR is built for the COCO recipe. On a short run it leaves
  the cosine phase empty and training stops with a `ValueError`. `train_worker.py` sets
  the three schedule bounds instead.
