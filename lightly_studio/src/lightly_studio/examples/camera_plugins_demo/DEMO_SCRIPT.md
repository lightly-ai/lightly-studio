# Demo script: 15 minutes, live

This is the run of show for the camera demo. It has three parts: the preparation, the
live demo, and the fallbacks.

The demo trains a model live. A run of 40 steps needs 4 to 8 minutes on a laptop CPU.
The script starts the training in minute 7 and fills the wait with the model of an
earlier run. Do not wait in silence for a training run.

## Part 1: Preparation, 20 minutes before the call

Prepare a data directory that already holds one trained model. The demo then has
something to deploy while the new run trains.

1. Start the camera source. For a webcam, go to step 2. For an RTSP simulation, run:

   ```bash
   ./simulate_rtsp_camera.sh my_video.mp4
   ```

2. Start the demo:

   ```bash
   python -m lightly_studio.examples.camera_plugins_demo.run_camera_demo \
       --source 0 \
       --data-dir ~/demo_data \
       --mqtt-host localhost \
       --hook-script src/lightly_studio/examples/camera_plugins_demo/example_hook.py
   ```

3. Collect 25 to 35 frames of the objects that you show in the call. Move the objects
   between the frames.
4. Label the frames in LightlyStudio. Use two classes, no more.
5. Run **Menu > Plugins > Train object detector**. Wait for the run to complete.
6. Make sure that the Eval tab shows the run.
7. Collect 5 more frames, but do not label them. The demo labels these on the call.
8. Open a terminal with the MQTT listener:

   ```bash
   python -m lightly_studio.examples.camera_plugins_demo.mqtt_listener --host localhost
   ```

Pre-flight checks:

- Camera access is granted to the terminal application. macOS asks once.
- The MQTT broker runs. `mosquitto` or `amqtt` are both sufficient.
- Ports 8001 and 8002 are free.
- Two browser windows are open: Camera Station and LightlyStudio.
- The window that shows the MQTT listener is visible next to the browser.

## Part 2: The live demo

### Minute 0 to 2: the camera feed

Show the Camera Station page.

> "This is a camera feed. It is a webcam here, but the same page takes an RTSP URL from
> a fixed camera. The server decodes the stream, so everything that follows works with
> any camera in the plant."

Click **Bookmark frame** 3 or 4 times while you move an object in front of the camera.
The counter increases with each click.

> "This is manual data collection. The operator watches the feed and keeps the frames
> that matter. Each frame goes into a dataset."

### Minute 2 to 5: the data in LightlyStudio

Switch to LightlyStudio. Reload the page.

> "The frames are here, in LightlyStudio. This is our product, not a demo screen."

1. Show the grid with the new frames. Point at the tag `bookmarked` in the filter panel.
2. Select the new frames. Assign the tag `line-a`.

   > "A tag is the project. One camera can feed many projects."

3. Show the Distr tab, or the metadata of one sample.

   > "Each frame keeps where it came from and how it was captured."

### Minute 5 to 7: labeling

Double-click one unlabeled frame.

1. Press `e` for edit mode. Press `b` for the bounding box tool.
2. Draw a box. Type the class name. Press Enter.
3. Press the right arrow key. Draw the next box.

Label 3 or 4 frames. Then stop.

> "This is the labeling that the customer does in Label Studio today. It is in the same
> tool as the data, so there is no export and no import."

### Minute 7 to 8: start the training

Go back to the grid. Open **Menu > Plugins**.

> "These five entries are the plugin interface of LightlyStudio. They are the code we
> wrote for this demo, about 1500 lines."

1. Open **Train object detector (LightlyTrain)**.
2. Show the parameters: the model, the steps, the batch size.
3. Click **Execute**. The dialog returns immediately with the run name.

> "Training runs in the background on the images of this view. LightlyTrain fine-tunes
> LT-DETR v2, which is our own detector."

### Minute 8 to 12: the model that is already trained

Switch to the Camera Station. The Models panel shows the new run with a progress bar.

> "While this trains, here is the model from the run I did before the call."

1. Select the earlier run in the Live detection panel. Click **Deploy**.
2. Move the object in front of the camera. The boxes follow it.

   > "Same feed, now with the model on it. 19 milliseconds per frame on this laptop."

3. Point at the MQTT terminal. The messages arrive.

   > "Each change of the object count is one MQTT message. A PLC, a line controller or a
   > light tower subscribes to this topic."

4. Show `example_hook.py` in the editor, then the event log line that it writes.

   > "If MQTT is not the protocol, the customer writes a Python function instead. This
   > one sends a stop signal when a person enters the frame."

5. Set **auto-bookmark low-confidence frames**. Show the tag `low-confidence` in
   LightlyStudio after a few frames.

   > "The model collects its own hard cases. These frames are the next labeling batch.
   > This is the data loop that we sell."

### Minute 12 to 15: the results of the new run

Switch to LightlyStudio and open the **Eval** tab.

1. Open the run with the name of the new model.
2. Show the configuration: the model, the steps, the number of images, the mAP.
3. Show the confusion matrix. Click one cell.

   > "The grid now shows the images of that cell. This is where the next labeling round
   > starts: the model tells you which images it gets wrong."

4. Go back to the Camera Station and deploy the new model.

> "That is the full loop: camera, frames, labels, model, deployment, signal. Steps 3 to 6
> are LightlyStudio and LightlyTrain as they ship. The camera page and the five plugins
> are the part that a customer project adds."

## Part 3: Fallbacks

| Problem | Action |
|---|---|
| The webcam does not open | Use `--source <video file>`. The file plays in a loop. |
| The training run is too slow | Keep the earlier model on the feed. Show the Eval tab of the earlier run. |
| The training run fails | Show the error in the Models panel. The earlier run stays available. |
| The MQTT broker is not there | Use only the Python hook. The event log of the page shows its output. |
| The grid does not show new frames | Reload the page. The grid has no push updates. |
| The model detects nothing | Lower the threshold to 0.25 in the Live detection panel. |

## What to say about the effort

- The demo is about 1500 lines of new Python and one HTML page.
- It adds no route and no component to LightlyStudio.
- Steps 3 to 6 of the customer workflow need no new code.
- A production version needs: user management, more than one camera, a real job queue
  for training, and an inference service that is separate from the interface.
