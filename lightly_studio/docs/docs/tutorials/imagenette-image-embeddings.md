# Explore and annotate Imagenette with embeddings

In this tutorial, you explore the Imagenette dataset in LightlyStudio and use image
similarity to guide labeling. Reviewing images one at a time is slow. Embeddings put
similar images next to each other, so you can review a whole group at once.

You will:

- Import 9,469 raw images across 10 classes.
- Explore the embedding plot and find groups of similar images.
- Use the lasso, the legend, and the `Color by` control to inspect those groups.
- Annotate a reviewed group.
- Load the ground truth of the dataset and measure your agreement with it.
- Export your work.

<!-- Screenshot 1: the embedding plot over the full dataset, with a hovered image preview.
Upload to https://storage.googleapis.com/lightly-public/studio/tutorials/imagenette-image-embeddings/embedding-overview.jpg
then replace this comment with:
![The embedding plot over the full Imagenette dataset](https://storage.googleapis.com/lightly-public/studio/tutorials/imagenette-image-embeddings/embedding-overview.jpg){ width="100%" }
-->

> **Screenshot 1 (placeholder):** The embedding plot over the full dataset, with a hovered
> image preview.

An embedding represents an image as a numerical vector. Images with similar visual or
semantic content get nearby embeddings. LightlyStudio projects these vectors into a
two-dimensional plot, where you can explore groups and inspect their images.

You do not need to annotate the entire dataset to finish this tutorial. Complete several
groups, export your progress, and return to the remaining images later.

## Step 1: Download the dataset

[Imagenette](https://github.com/fastai/imagenette) is a subset of ImageNet with 10 classes,
assembled by fast.ai. The classes are easy to tell apart, which makes the dataset a good
fit for this workflow: you can recognize a church or a parachute without a reference.

This tutorial uses the 320 px variant, where each image has a shortest side of 320 pixels.

Save the following as `download_imagenette.py` in a working directory:

```python title="download_imagenette.py"
import tarfile
from pathlib import Path

from lightly_studio.dataset import file_utils

IMAGENETTE_URL = "https://s3.amazonaws.com/fast-ai-imageclas/imagenette2-320.tgz"
ARCHIVE = Path("imagenette2-320.tgz")
DATA_DIR = Path("data")
# Touched only after extractall returns, so an interrupted extraction is not
# mistaken for a complete one.
EXTRACT_DONE = DATA_DIR / ".extracted"
IMAGE_PATH = DATA_DIR / "imagenette2-320" / "train"


def download_dataset() -> None:
    # The helper downloads to a temp file and moves it into place only on success,
    # so an interrupted download is never mistaken for a complete one.
    file_utils.download_file_if_does_not_exist(url=IMAGENETTE_URL, local_filename=ARCHIVE)
    if not EXTRACT_DONE.exists():
        with tarfile.open(ARCHIVE) as tar:
            # filter="data" refuses members that would write outside DATA_DIR.
            # Python 3.12 and newer apply this filter by default. Older versions
            # accept the argument from 3.9.17, 3.10.12, and 3.11.4 onwards.
            if hasattr(tarfile, "data_filter"):
                tar.extractall(DATA_DIR, filter="data")
            else:
                tar.extractall(DATA_DIR)
        EXTRACT_DONE.touch()


if __name__ == "__main__":
    download_dataset()
```

Run it:

```bash
python download_imagenette.py
```

The archive is about 342 MB and expands to about 359 MB. Keep about 700 MB of free disk
space, because both the archive and the extracted folder are present after the run. Delete
`imagenette2-320.tgz` afterwards if you need the space.

!!! note "Extraction safety"
    `filter="data"` refuses archive members that would write outside `data/`. Python 3.12
    and newer apply this filter by default. The script only passes the argument when your
    Python version supports it, so it also runs on older versions.

The extracted dataset has this layout:

```text
imagenette-tutorial/
├── download_imagenette.py
├── imagenette2-320.tgz
└── data/
    └── imagenette2-320/
        ├── noisy_imagenette.csv
        ├── train/
        │   ├── n01440764/
        │   │   ├── n01440764_10026.JPEG
        │   │   └── ...
        │   └── ...
        └── val/
```

The archive holds 13,394 images in two splits: 9,469 in `train/` and 3,925 in `val/`. This
tutorial imports `train/` only. The `val/` split stays on disk for later use.

Each split has one folder per class, named by its WordNet ID. Use this table to find the
class of a folder:

| Folder | Class |
| --- | --- |
| n01440764 | tench |
| n02102040 | English springer |
| n02979186 | cassette player |
| n03000684 | chain saw |
| n03028079 | church |
| n03394916 | French horn |
| n03417042 | garbage truck |
| n03425413 | gas pump |
| n03445777 | golf ball |
| n03888257 | parachute |

The `train/` split has between 858 and 993 images per class.

The folder name is also the ground truth of the dataset. In step 8 you load it into
LightlyStudio and compare it against your own work.

`noisy_imagenette.csv` holds the same reference classes, together with variants that have
deliberate noise. This tutorial does not use the file. Keep it if you want to experiment with
noisy annotations later.

Imagenette is a subset of ImageNet, so the terms of ImageNet apply to the images. See the
[Imagenette repository](https://github.com/fastai/imagenette) for its license note.

## Step 2: Import the images

Install LightlyStudio in your Python environment:

```bash
pip install lightly-studio
```

Save the following as `explore_imagenette.py` in the same working directory:

```python title="explore_imagenette.py"
import lightly_studio as ls

if __name__ == "__main__":
    dataset = ls.ImageDataset.load_or_create(name="imagenette")
    # 9,469 images. The first run also downloads the embedding model.
    # Add limit=1000 for a faster first pass.
    dataset.add_images_from_path(path="data/imagenette2-320/train", tag_depth=1)
    ls.start_gui()
```

Run it from that directory:

```bash
python explore_imagenette.py
```

LightlyStudio indexes the raw images and computes image embeddings during ingestion.
`add_images_from_path` embeds by default, so there is no separate step and no button in
the GUI to compute embeddings. The first run needs time to download the embedding model
and process every image.

Wait for ingestion to finish and check the output for skipped images before you continue.
Resolve any skipped files rather than treating the import as complete.

`tag_depth=1` tags each image with the name of its first folder below the import path. Each
image gets one tag, its WordNet ID. These tags come from the dataset, not from annotations
that you created. This tutorial asks you to annotate the images from what you see in them, so
leave the tags alone until step 8.

Embeddings and annotations persist in `lightly_studio.db` in the working directory.
Rerunning the script with the same database and dataset name reuses existing samples and
embeddings, and skips images that are already present. Keep the original images at their
imported paths.

If you already have embeddings, follow
[Loading precomputed embeddings](../core_concepts/embeddings.md#loading-precomputed-embeddings)
instead. Register the custom generator before ingestion.

## Step 3: Explore the embedding plot

Click **Embed** in the right-hand tab rail to open the embedding plot. Each point is one
image, placed by a two-dimensional projection (PaCMAP) of its embedding.

!!! note "No Embed tab?"
    The tab only appears when the dataset has embeddings. If it is missing, ingestion ran
    with `embed=False` or the embedding model failed to download. Check the output of
    step 2.

1. Scroll to zoom, and drag to pan.
2. Hover over several points to preview their images.
3. Look for shared characteristics: object shape, scene type, indoor or outdoor, and
   background.
4. Compare one group with another elsewhere in the plot.

The projection is approximate. It keeps local neighborhoods, not distances. A visible
group is not necessarily one class, and one class can appear in several groups. Treat
proximity as a reason to inspect images together, not as proof that they share an
annotation class.

## Step 4: Annotate a few reference examples

Choose a few clearly identifiable images from several classes. Parachutes, churches, and
garbage trucks are easy to recognize, but use whichever examples you can identify
confidently.

Open an image's detail view and use **Add classification** to assign its class as an
annotation class. Put every annotation that you create into one annotation source, named
`my_labels`. Step 9 compares that source against the ground truth.

Use these exact annotation class names:

```text
tench              chain_saw    garbage_truck    golf_ball
english_springer   church       gas_pump         parachute
cassette_player    french_horn
```

!!! warning "The names must match exactly"
    Step 9 compares annotation classes as text. If you write `garbage truck` here and the
    ground truth says `garbage_truck`, every image of that class counts as a disagreement.
    Copy the names from this list.

Annotate two or three clear examples for each class you choose. If you are unsure about an
image, consult the class table in step 1, or leave the image for later review.

These examples give you visual references for exploring nearby raw images. This is a
manual workflow: reference annotations do not classify their neighbors automatically.

## Step 5: Lasso and inspect a group

The plot toolbar has a lasso button and a rectangle button. You can also select without
leaving normal mode:

| Gesture | Result |
| --- | --- |
| Shift + drag | Rectangle selection. |
| Shift + Cmd + drag (Ctrl on Windows) | Freehand lasso selection. |

Draw around a small group near one of your reference examples. On release, the image grid
scopes to the samples in that region, and an **Embedding Plot Filter** entry appears in
the sidebar with the count.

A lasso scopes the grid. It does not create annotations, and the plot keeps showing every
point, highlighting the ones inside your region.

!!! tip "Select a region, not everything"
    A selection that covers every point counts as no filter, and the grid does not change.
    If nothing happens, your lasso was probably too wide.

Press **Esc** to clear the selection.

Review the images in the scoped grid. Open unclear thumbnails in detail view. Exclude
other classes and ambiguous images. Start with a small group so you can inspect every
sample.

<!-- Screenshot 2: a lasso region beside its scoped image grid.
Upload to https://storage.googleapis.com/lightly-public/studio/tutorials/imagenette-image-embeddings/lasso-scoped-grid.jpg -->

> **Screenshot 2 (placeholder):** A lasso region beside its scoped image grid.

## Step 6: Annotate the reviewed group

The lasso scoped the grid to one region. Now annotate the images you reviewed.

Open the first image in the scoped grid, assign its class with **Add classification**,
and use the arrow keys to step to the next image. Use the same annotation class names and the
same `my_labels` annotation source as your reference examples.

Each image still takes one action. The gain is that you no longer hunt for related
images or decide what each one is: the group already shares a class, so you confirm
rather than classify from scratch. Skip any image that does not belong to the class.

Open several annotated images again and confirm their classifications before you move on.

Repeat for another group:

1. Press **Esc** to clear the region.
2. Find another group of similar images.
3. Review the scoped grid.
4. Annotate the images that belong to the class.

Visual similarity suggests candidates. Your review decides which images get the
annotation.

<!-- Screenshot 3: the detail view with Add classification open on a scoped image.
Upload to https://storage.googleapis.com/lightly-public/studio/tutorials/imagenette-image-embeddings/add-classification.jpg -->

> **Screenshot 3 (placeholder):** The detail view with **Add classification** open on an
> image from the scoped group.

## Step 7: Use the legend and restore the view

Once you have created annotations, open **Color by** below the plot and choose
**annotations**. The plot colors each point by its annotation class, and a legend appears
in the bottom-left corner.

| Control | Try it | Effect |
| --- | --- | --- |
| Hover | Hover over a point. | Preview its image. |
| Legend single-click | Click a class entry, then click it again. | Hide, then show its points. |
| Legend double-click | Double-click a class entry. | Isolate that class. |
| Restore classes | Double-click the isolated entry again. | Show the other classes again. |
| Reset zoom | Click **Reset zoom**. | Restore the viewport. |

The legend also has reserved entries below a divider, such as **No category** for samples
with no annotation. These toggle on a single click, but double-click does not isolate
them.

!!! warning "Color by resets the legend"
    Changing **Color by** clears which classes you hid, because LightlyStudio reassigns
    the color slots.

Legend visibility, dataset filters, the lasso region, and the viewport are separate
controls. Hiding a class does not delete its images or annotations, and **Reset zoom**
only restores the viewport. To return to an unrestricted view:

1. Press **Esc** to clear the lasso region.
2. Show any hidden legend entries again.
3. Clear active dataset filters.
4. Click **Reset zoom**.

<!-- Screenshot 4: the plot colored by annotations with one class isolated.
Upload to https://storage.googleapis.com/lightly-public/studio/tutorials/imagenette-image-embeddings/legend-isolated.jpg -->

> **Screenshot 4 (placeholder):** The plot colored by annotations, with one class isolated
> in the legend.

## Step 8: Load the ground truth

Until now you annotated the images from what you see. Imagenette also ships a reliable class
for every image, in its folder names. Load that as a second annotation source, then compare
the two.

Stop the GUI with ++ctrl+c++. Save the following as `load_ground_truth.py` in the same working
directory:

```python title="load_ground_truth.py"
from pathlib import Path

import lightly_studio as ls
from lightly_studio.core.annotation import CreateClassification

# The folder names of Imagenette are WordNet IDs. These are the annotation class
# names from step 4.
WORDNET_TO_CLASS = {
    "n01440764": "tench",
    "n02102040": "english_springer",
    "n02979186": "cassette_player",
    "n03000684": "chain_saw",
    "n03028079": "church",
    "n03394916": "french_horn",
    "n03417042": "garbage_truck",
    "n03425413": "gas_pump",
    "n03445777": "golf_ball",
    "n03888257": "parachute",
}

if __name__ == "__main__":
    dataset = ls.ImageDataset.load(name="imagenette")
    for sample in dataset:
        wordnet_id = Path(sample.file_path_abs).parent.name
        sample.add_annotation(
            CreateClassification(class_name=WORDNET_TO_CLASS[wordnet_id]),
            annotation_source="ground_truth",
        )
    print("Ground truth loaded.")
```

Run it:

```bash
python load_ground_truth.py
```

The script writes one classification for each of the 9,469 images. This takes about one
minute. LightlyStudio creates the ten annotation classes when it first reads each name, so
there is no separate step for that.

The `ground_truth` source is separate from your `my_labels` source. It does not change or
overwrite the annotations that you created.

!!! warning "Run this script one time only"
    `add_annotation` appends to an annotation source. A second run gives every image a second
    ground truth annotation. If you must run it again, delete the `ground_truth` source in the
    GUI first.

## Step 9: Compare your annotations against the ground truth

An evaluation run compares two annotation sources and stores a metric for each image. Add
this to the end of `load_ground_truth.py`, inside the `if __name__ == "__main__":` block:

```python title="load_ground_truth.py"
    result = dataset.evaluate().classification(
        name="imagenette-review",
        gt_annotation_source="ground_truth",
        pred_annotation_source="my_labels",
    )
    print(f"Compared {result.sample_count} images.")
    ls.start_gui()
```

An evaluation run uses only the images that are in both annotation sources. Your run therefore
covers the images that you annotated, and no others. Images that you did not annotate are
skipped. They do not count as errors.

Open the **Evaluation** panel in the GUI and select the `imagenette-review` run:

1. Read the confusion matrix. Green cells on the diagonal are images where you and the ground
   truth agree.
2. Find the red cells off the diagonal. These are the classes that you and the ground truth
   assigned differently.
3. Sort the image grid by `disagreement` to put those images first.
4. Open them in detail view and compare what you see against both annotation classes.

A red cell is not always your error. Some Imagenette images contain more than one of the ten
classes, such as a golf ball on grass beside a person. The confusion matrix shows you where
visual similarity and annotation class stop agreeing. These are the images that a labeling
workflow gets wrong most often.

<!-- Screenshot 5: the confusion matrix of the imagenette-review evaluation run.
Upload to https://storage.googleapis.com/lightly-public/studio/tutorials/imagenette-image-embeddings/confusion-matrix.jpg -->

> **Screenshot 5 (placeholder):** The confusion matrix of the `imagenette-review` evaluation
> run, with one red off-diagonal cell.

For more about evaluation runs and their metrics, see
[Model Evaluation](../workflows/evaluation.md).

## Step 10: Save and export your progress

LightlyStudio persists your annotations in its database. To resume later, rerun
`explore_imagenette.py` from the same working directory. Open an annotated image to verify
that its classification is still there. See
[Reuse Datasets](../get_started/reuse_datasets.md).

To export your classifications:

1. Clear temporary filters and selections, so you export the scope you intend.
2. Open **Menu → Export**.
3. Choose **Image Classifications (CSV)** and the `my_labels` annotation source.
4. Export the file, then check several image paths and their classes against the GUI.

Select `my_labels` and not `ground_truth`. The `ground_truth` source is the reference that you
loaded in step 8, not the work that you did.

The CSV contains classifications and image paths. It does not package the image files, so
keep the original images and the database. Images you have not annotated stay available
for later work.

For more export options, see [Export](../workflows/export.md).

## Conclusion

You imported 9,469 raw images, explored their embeddings, and used groups of similar
images to guide labeling. Instead of deciding what every image shows, you reviewed related
images together and confirmed a shared annotation class. Then you loaded the ground truth of
the dataset and measured where your annotations and the ground truth disagree.

Continue with more groups until you reach the coverage you need. Run the evaluation again
after each session. The confusion matrix shows whether your accuracy holds as you move into
groups that are harder to tell apart.

A follow-up workflow could use embeddings and a small set of annotated examples to
generate nearest-neighbor suggestions. Keep suggestions in their own annotation source
and inspect them before you accept them.

Related guides: [Embeddings](../core_concepts/embeddings.md),
[Image Dataset](../workflows/image_dataset.md), and
[Annotations](../workflows/annotations.md).
