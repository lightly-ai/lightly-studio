# Train a model from LightlyStudio (prototype)

This guide tells you how to train an object detection model from the GUI with
[LightlyTrain](https://docs.lightly.ai/train/stable/index.html).

## What it does

In the GUI, "Menu > Train model" does these steps:

1. It trains PicoDet-S (`picodet-s-coco`) on the images of a train tag. It validates on the images
   of a val tag.
2. It predicts boxes on all images of the collection. It keeps the boxes with a score of 0.5 or more.
3. It adds the predictions as a new annotation source with the name `lightly_train_<timestamp>`.
4. It evaluates the predictions on the val tag. The evaluation run has the same name.

The menu item shows only for image collections, only for users with the editor role or higher, and
only when training is on (see step 1 below).

## 1. Install LightlyTrain

You need LightlyTrain 0.18.0 or newer. Older versions do not have PicoDet.

**Option A: a separate virtual environment (recommended).** This keeps the dependencies of
LightlyStudio and LightlyTrain apart.

```bash
uv venv ~/lightly-train-venv --python 3.12
uv pip install --python ~/lightly-train-venv/bin/python "lightly-train>=0.18.0"
```

Then tell LightlyStudio which Python to use. Add this line to `lightly_studio/.env`, or export it
in your shell:

```bash
LIGHTLY_STUDIO_TRAINING_PYTHON=/Users/<you>/lightly-train-venv/bin/python
```

Use an absolute path. LightlyStudio does not expand `~` in this variable.

The training process needs only `lightly_train` and `torch`. It does not import `lightly_studio`.

**Option B: the Python of LightlyStudio.** Install `lightly-train` in the same environment as
LightlyStudio. You do not need `LIGHTLY_STUDIO_TRAINING_PYTHON` then.

## 2. Build the frontend

`ls.start_gui()` serves the built frontend from `src/lightly_studio/dist_lightly_studio_view_app`.
This build can be older than your code. To use the current frontend, do one of these:

- Build it (this takes several minutes):

  ```bash
  cd lightly_studio
  make build-lightly_studio_view
  ```

- Or start the Vite dev server after the backend is running:

  ```bash
  cd lightly_studio_view
  PUBLIC_SAMPLES_URL=http://localhost:8001/images npx vite dev
  ```

## 3. Start the example

> **Warning:** The example deletes your local LightlyStudio database.

```bash
cd lightly_studio
uv run src/lightly_studio/examples/example_train_model.py
```

The example reads `EXAMPLES_COCO_JSON_PATH` and `EXAMPLES_COCO_IMAGES_PATH` from `lightly_studio/.env`
(see `.env.example`). It adds the COCO subset with two annotation classes, "human" and "animal", in
the annotation source `ground_truth`. It tags 60 % of the images `train` and 20 % `val`. The other
20 % have no tag and no annotations. Then it starts the GUI.

## 4. Train in the GUI

1. Open the collection, then "Menu > Train model".
2. Select these values:
   - Train tag: `train`
   - Val tag: `val`
   - Ground truth annotation source: `ground_truth`
   - Steps: 100 is the default. Use a small number, for example 20, for a quick test.
3. Click "Start training".

The run card shows the stage: Training, Predicting on all images, Adding predictions, Evaluating
on the val tag, and then Completed. "Cancel" stops the training process. Only one run can be
active at a time.

When the run is completed, the predictions are in the new annotation source, and the evaluation
results are in the evaluation run with the same name.

## Use your own data

You can train on each image collection that has:

- An object detection annotation source with the ground truth.
- Two different tags that are not empty, one for training and one for validation. "Split dataset"
  can make these tags.

## Run files

Each run has a folder `lightly_studio_training_runs/<run_id>/`. The path is relative to the
working directory. To change it, set `LIGHTLY_STUDIO_TRAINING_RUNS_DIR`.

| File | Contents |
| --- | --- |
| `config.json` | The config that the training process reads |
| `train.json`, `val.json` | The ground truth of the train and val images, in COCO format |
| `predict_images.json` | The images to predict on |
| `stage.txt` | The current stage: `training` or `predicting` |
| `process.log` | The output of the training process |
| `predictions.json` | The predictions |
| `lightly_train/train.log` | The LightlyTrain log with the training progress |
| `lightly_train/exported_models/` | The trained model: `exported_best.pt`, or `exported_last.pt` if there is no best model |

## Device and settings

The training process uses a CUDA GPU if it can, then Apple MPS, then the CPU. It uses one device
and a batch size of 16. The settings are in `training_runner.py`.

Training uses no data augmentation. It resizes the images to 416×416 and normalizes them, the same
as validation. The precision is bf16 mixed on CUDA and MPS (fp16 mixed on CUDA GPUs without bf16),
and 32-bit on the CPU.

## Troubleshooting

| Problem | Solution |
| --- | --- |
| "Train model" is not in the menu | LightlyStudio did not find LightlyTrain, and `LIGHTLY_STUDIO_TRAINING_PYTHON` is not set. Set it, then restart LightlyStudio. |
| The run status is "Failed" | Read `process.log` in the run folder. |
| The GPU is out of memory | Make `_TRAIN_BATCH_SIZE` in `training_runner.py` smaller. |
