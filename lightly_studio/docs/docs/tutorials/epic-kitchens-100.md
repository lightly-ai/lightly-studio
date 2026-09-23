# Explore EPIC-KITCHENS-100 Video Clips in LightlyStudio

EpicKitchens dataset has gained popularity in the computer vision community for its rich annotations for a set of egocentric videos, designed to develop models for robotics-related tasks. In this tutorial, we show how to preprocess the EpicKitchens dataset and visualize it in LightlyStudio.

At the end, we will have loaded and explored a dataset of more than 37000 video clips, each with a caption describing the action in the clip. We show how to explore the embedding plot and slice and dice the dataset for further analysis.

![Selecting video clips in the LightlyStudio embedding plot](https://cdn.prod.website-files.com/62cd5ce03261cb3e98188470/69b01574349707d3b4f67b82_00_selection.gif){ width="100%" }

## Understanding Different EpicKitchens Datasets

For a newcomer, the structure of the EpicKitchens dataset can be a bit overwhelming. In fact, EpicKitchens is a **collection of datasets**, each with its own structure and annotations, and different ways to access the data.

The main datasets with video recordings are:

- **EPIC-KITCHENS-55**
    - 55 hours of videos collected with a head-mounted GoPro camera by multiple participants in their kitchens
    - Video segments annotated with action labels (verb-noun pairs) and free-form captions
    - Released in 2018
    - Hosted on DataBris: [https://data.bris.ac.uk/data/dataset/3h91syskeag572hl6tvuovwv4d](https://data.bris.ac.uk/data/dataset/3h91syskeag572hl6tvuovwv4d)
- **EPIC-KITCHENS-100**
    - Extension of EPIC-KITCHENS-55 with more participants, and more annotations for a total of 100 hours of videos
    - Released in 2020
    - Website: [https://epic-kitchens.github.io/](https://epic-kitchens.github.io/)
    - Hosted on DataBris: [https://data.bris.ac.uk/data/dataset/2g1n6qdydwa9u22shpxqzp0t8m](https://data.bris.ac.uk/data/dataset/2g1n6qdydwa9u22shpxqzp0t8m)
- **HDEpic**
    - 41 hours of egocentric videos collected with an Aria headset
    - Compared with EPIC-KITCHENS, it has denser annotations and also provides 3D digital twins of the scenes, and more
    - Released in 2025
    - Website: [https://hd-epic.github.io/](https://hd-epic.github.io/)
    - Hosted on DataBris: [https://data.bris.ac.uk/data/dataset/3cqb5b81wk2dc2379fx1mrxh47](https://data.bris.ac.uk/data/dataset/3cqb5b81wk2dc2379fx1mrxh47)

Moreover, separate, derived datasets annotating the data from EPIC-KITCHENS-100 are available, such as:

- **VISOR** - Dense instance segmentation annotations
- **EPIC-Sounds** - Audio annotations
- **EPIC-Fields** - 3D digital twins

## Downloading EPIC-KITCHENS-100

For our tutorial we focus on EPIC-KITCHENS-100 and download videos and annotated actions.

!!! note
    You can skip the downloading and preprocessing steps if you are only interested in the final result. We uploaded it as the [lightly-ai/epic-kitchens-100-clips dataset](https://huggingface.co/datasets/lightly-ai/epic-kitchens-100-clips) to HuggingFace (24GB).

### Download Videos

The first obstacle is that EPIC-KITCHENS-55 videos and the extension part of EPIC-KITCHENS-100 are distributed separately. For simplicity, we focus on **the extension part of EPIC-KITCHENS-100**.

The videos are officially hosted on DataBris servers, but the mirrors are slow. Luckily, the extension dataset is also available via AcademicTorrents and HuggingFace, we are going to use the HuggingFace mirror:

```bash
# Install HuggingFace CLI according to https://huggingface.co/docs/huggingface_hub/en/guides/cli
curl -LsSf https://hf.co/cli/install.sh | bash

# Download videos (464 GB)
hf download awsaf49/epic_kitchens_100 --repo-type dataset --include "*.MP4" --local-dir ./EPIC-KITCHENS-100
```

The download size is big. To follow along, you can download a subset of the videos with the official downloader, as follows:

```bash
# Clone the helper repo for downloading videos
git clone https://github.com/epic-kitchens/epic-kitchens-download-scripts.git
cd epic-kitchens-download-scripts

# Download the 10 shortest videos
python epic_downloader.py \
    --videos \
    --specific-videos P03_15,P03_26,P06_02,P09_01,P26_30,P04_19,P07_106,P03_110,P02_05,P26_12 \
    --output-path ../EPIC-KITCHENS-100
```

### Download Action Annotations

The action annotations are available in the `epic-kitchens-100-annotations` repository, which we simply clone:

```bash
git clone https://github.com/epic-kitchens/epic-kitchens-100-annotations.git
```

### Verify the Folder Structure

After downloading, you should have the following folder structure. The videos are organized by participants `P01 - P37`, and each participant has a `videos` folder with the video files. The action annotations are in the `epic-kitchens-100-annotations` folder in `EPIC_100_train.csv` and `EPIC_100_validation.csv` files.

```text
.
├── EPIC-KITCHENS-100/
│   ├── P01/
│   │   └── videos/
│   │       ├── P01_101.MP4
│   │       └── ...
│   └── ...
└── epic-kitchens-100-annotations/
    ├── EPIC_100_train.csv
    ├── EPIC_100_validation.csv
    └── ...
```

## Preprocessing the Videos

We cut the videos into clips, one for each annotated action. The annotations provide the start and end times of each action, an example annotation looks like this:

```text
narration_id,participant_id,video_id,narration_timestamp,start_timestamp,stop_timestamp,start_frame,stop_frame,narration,verb,verb_class,noun,noun_class,all_nouns,all_noun_classes
P01_102_0,P01,P01_102,00:00:01.100,00:00:00.54,00:00:02.23,27,111,take knife and plate,take,0,knife,4,"['knife', 'plate']","[4, 2]"
```

We have let an AI assistant write a Python script which loads the annotations from the two files with `pandas`, and then calls `ffmpeg` to cut the clips from the videos. We also downsized the videos to 854x480px.

We uploaded [the script](https://huggingface.co/datasets/lightly-ai/epic-kitchens-100-clips/blob/main/cut_clips.py) together with its outputs as the [lightly-ai/epic-kitchens-100-clips dataset](https://huggingface.co/datasets/lightly-ai/epic-kitchens-100-clips) to HuggingFace. You can run it as follows, make sure ffmpeg is already installed on your system:

```bash
pip install pandas tqdm
python cut_clips.py
```

It expects the folder structure described above, and creates a clips folder with the cut clips, named by their narration ID, e.g. `clips/P01/P01_102_0.mp4` for the example annotation above.

!!! note
    For the 464 GB dataset of videos, the script ran for about 8.5 hours on a 47-core machine, not exhaustively using all cores. It created 37455 clips, with a total size of 24 GB.

## Loading the Clips in LightlyStudio

Now the difficult part is done, and we are ready to load the clips in LightlyStudio. First we install dependencies, we use `pandas` for loading annotations and `tqdm` for displaying progress:

```bash
pip install lightly-studio pandas tqdm
```

Create a Python script `load_clips.py` with the following content:

```python title="load_clips.py"
import lightly_studio as ls
import pandas as pd
from tqdm import tqdm

# Load video clips into a LightlyStudio dataset
dataset = ls.VideoDataset.load_or_create()
dataset.add_videos_from_path(path="./clips")

# Load narration CSVs
train_csv = pd.read_csv("./epic-kitchens-100-annotations/EPIC_100_train.csv")
val_csv = pd.read_csv("./epic-kitchens-100-annotations/EPIC_100_validation.csv")
file_name_to_row = {}
for _, row in pd.concat([train_csv, val_csv], ignore_index=True).iterrows():
    filename = f"{row['narration_id']}.mp4"
    file_name_to_row[filename] = row.to_dict()

# Add metadata to each video
for video in tqdm(dataset, "Loading annotations"):
    row = file_name_to_row[video.file_name]

    # Add a caption
    video.add_caption(row["narration"])

    # Add metadata
    for key, value in row.items():
        video.metadata[key] = value

# Start the LightlyStudio GUI
ls.start_gui()
```

We first create a video dataset and add the videos from the clips folder. Then we load the annotations from the two CSV files into a mapping from file name to CSV row. Finally, we loop through the videos in the dataset and add the `narration` column as the video caption, and populate video metadata with all the other columns from the CSV. Finally, we start the LightlyStudio GUI:

```bash
python load_clips.py
```

Once the data is loaded, it is persisted in the `lightly_studio.db` file. The GUI server can be safely stopped by pressing Ctrl+C in the terminal, and restarted by calling `ls.start_gui()` again:

```bash
python -c "import lightly_studio as ls; ls.start_gui()"
```

!!! note
    Loading annotations one-by-one can be very slow. To process the whole dataset, we used a more optimised version of the script with bulk inserts. You can find it [on HuggingFace](https://huggingface.co/datasets/lightly-ai/epic-kitchens-100-clips/blob/main/lightly_studio_2_load_anotations_fast.py).

## Exploring EpicKitchens with LightlyStudio

### Get a Quick Overview

On the initial screen, we see a grid of all the videos together with their captions. The bottom left shows that we loaded 37455 videos. We can hover over each video to see it playing, and double-click to open the video details page. There we can see all metadata loaded from the CSV.

![Grid view of the EPIC-KITCHENS-100 video clips](https://cdn.prod.website-files.com/62cd5ce03261cb3e98188470/69b014edb344464e241c7644_01_grid_view.gif){ width="100%" }

Captions can be also inspected in a dedicated tab, where long captions are displayed in full. If there were multiple captions per video, they would all be displayed here. Caption editing is supported.

![Caption editing in LightlyStudio](https://cdn.prod.website-files.com/62cd5ce03261cb3e98188470/699c250b9e2f67547df17d93_02_captions_800%20(1).gif){ width="100%" }

### Understand the Dataset

LightlyStudio computes embeddings with the [Perception Encoder model](https://github.com/facebookresearch/perception_models) for all the videos, so that they can be easily visualized and searched. In the embedding plot, which shows embeddings projected to 2D with PacMAP, we see that the videos are organized in clusters. We can lasso-select a cluster to see which videos are in it. Selected data can be easily tagged.

![Lasso selection of a cluster in the embedding plot](https://cdn.prod.website-files.com/62cd5ce03261cb3e98188470/69b015125d280736cfcbbc9f_03_embeddings_1080.gif){ width="100%" }

We can also use text search to find videos with specific content. When submitting a query, the text is embedded with Perception Encoder and compared with indexed video embeddings stored in a local database for high performance. You can notice the similarity score between zero and one shown for every video.

![Text search over the video clips](https://cdn.prod.website-files.com/62cd5ce03261cb3e98188470/69b015daec76fdb40df5a8ee_04_text_search.gif){ width="100%" }

The dataset is quite big to scroll through fully. To get an overview of samples in it, we can use the "Selection" feature to get a smaller, representative sample. Navigate to Menu → Selection and choose 100 videos using the "Diversity" strategy. This performs the selection in Rust, selected images are tagged with a chosen tag. Note that the selection takes about one minute, we cut the waiting time from the gif below.

![Diversity selection of 100 video clips](https://cdn.prod.website-files.com/62cd5ce03261cb3e98188470/69b014bbdc2b6df1f56b8e61_05_selection_1080.gif){ width="100%" }

## Conclusion

To summarise, we have shown how to:

- Overcome the difficulties of loading the EPIC-KITCHENS-100 dataset
- Preprocess the videos into clips corresponding to annotated actions
- Load and explore the dataset in LightlyStudio

This only scratches the surface of the capabilities of LightlyStudio. To see how to edit captions, export the annotations, and more, check out the rest of this documentation, for example [Add Captions](../workflows/captions.md), [Sampling](../workflows/sampling.md), and [Export](../workflows/export.md).
