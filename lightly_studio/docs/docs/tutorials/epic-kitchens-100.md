# QA Egocentric Video Data with Epic-Kitchens-100

In this tutorial, we show how to do QA on a large egocentric video dataset with LightlyStudio. We use EPIC-KITCHENS-100: more than 37000 video clips of kitchen activities, each with a narration that describes the action in the clip.

We show how to:

- Download the preprocessed clips and narrations from HuggingFace and load them into LightlyStudio
- Explore the dataset with the embedding plot, text search, and sampling
- Find near-duplicate clips and correlations with the embedding plot and metadata
- Find low-quality clips, for example dark or blurry clips
- Find narrations that do not match the video, with a plugin that calculates the alignment between the narration and the video

<video autoplay loop muted playsinline controls style="width: 100%;" onloadedmetadata="this.defaultPlaybackRate = 2; this.playbackRate = 2;">
  <source src="https://storage.googleapis.com/lightly-public/studio/tutorials/epic-kitchen/epickitchen_overview_full.mp4" type="video/mp4">
</video>

We recorded the videos in this tutorial on a Linux server with an NVIDIA RTX 4090 GPU. The video above plays at 2x speed. For the processing times, see [Run the Loading Scripts](#run-the-loading-scripts).

## Understanding Different EpicKitchens Datasets

EpicKitchens is a collection of datasets. The main datasets with egocentric video recordings are:

| Dataset | Released | Videos | Description |
|---|---|---|---|
| [EPIC-KITCHENS-55](https://data.bris.ac.uk/data/dataset/3h91syskeag572hl6tvuovwv4d) | 2018 | 55 hours | Recorded with a head-mounted GoPro, with action labels and narrations |
| [EPIC-KITCHENS-100](https://epic-kitchens.github.io/) | 2020 | 100 hours | Extends EPIC-KITCHENS-55 with more participants and annotations |
| [HD-EPIC](https://hd-epic.github.io/) | 2025 | 41 hours | Recorded with an Aria headset, with denser annotations and 3D digital twins |

Other datasets add annotations to EPIC-KITCHENS-100, for example VISOR (instance segmentation), EPIC-Sounds (audio), and EPIC-Fields (3D digital twins). In this tutorial, we use EPIC-KITCHENS-100.

## Download the Clips from HuggingFace

We have already cut the EPIC-KITCHENS-100 videos into clips and uploaded them together with the annotations and the loading scripts as the [lightly-ai/epic-kitchens-100-clips dataset](https://huggingface.co/datasets/lightly-ai/epic-kitchens-100-clips) to HuggingFace. It contains:

- `clips/`: 37455 video clips (24 GB), one for each annotated action, stored as `{participant_id}/{narration_id}.mp4`. The clips are downscaled to 854x480px.
- `epic-kitchens-100-annotations/`: The original action annotations in `EPIC_100_train.csv` and `EPIC_100_validation.csv`.
- `requirements.txt`: The Python dependencies for the loading scripts.
- `lightly_studio_1_load_videos.py`, `lightly_studio_2_load_anotations_fast.py`, `lightly_studio_3_start_gui.py`: Scripts to load the clips into LightlyStudio and start the GUI.
- `embedding_model.py`: Loads the large Perception Encoder model, which the scripts use to embed the clips and the text queries.
- `caption_similarity_plugin.py`: A plugin that calculates the alignment score between the narration and the video of each clip.
- `cut_clips.py`: The script that we used to cut the clips from the original videos.

!!! note
    The dataset is published under the [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/) license, the same as the original EPIC-KITCHENS-100 dataset. You cannot use it for commercial purposes.

Download the dataset (24 GB) with the HuggingFace CLI or with Git:

=== "HuggingFace CLI"

    Install the [HuggingFace CLI](https://huggingface.co/docs/huggingface_hub/en/guides/cli) and download the dataset:

    ```bash
    # Install HuggingFace CLI
    curl -LsSf https://hf.co/cli/install.sh | bash

    # Download clips, annotations, and scripts
    hf download lightly-ai/epic-kitchens-100-clips \
        --repo-type dataset \
        --local-dir ./epic-kitchens-100-clips
    ```

=== "Git"

    HuggingFace stores the large files with Xet. Install [Git LFS](https://git-lfs.com/) and the [Git Xet extension](https://huggingface.co/docs/hub/git-xet), then clone the dataset:

    ```bash
    # Install Git LFS and Git Xet (macOS, for other systems see the links above)
    brew install git-lfs git-xet
    git lfs install
    git xet install

    # Clone clips, annotations, and scripts
    git clone https://huggingface.co/datasets/lightly-ai/epic-kitchens-100-clips
    ```

After the download, you have the following folder structure:

```text
epic-kitchens-100-clips/
├── clips/
│   ├── P01/
│   │   ├── P01_102_0.mp4
│   │   └── ...
│   └── ...
├── epic-kitchens-100-annotations/
│   ├── EPIC_100_train.csv
│   └── EPIC_100_validation.csv
├── caption_similarity_plugin.py
├── cut_clips.py
├── embedding_model.py
├── lightly_studio_1_load_videos.py
├── lightly_studio_2_load_anotations_fast.py
├── lightly_studio_3_start_gui.py
└── requirements.txt
```

??? note "How we created the clips from the original EPIC-KITCHENS-100 videos"
    You do not need these steps to follow the tutorial. They show how we created the clips on HuggingFace from the original videos.

    **Download the videos**

    The first obstacle is that EPIC-KITCHENS-55 videos and the extension part of EPIC-KITCHENS-100 are distributed separately. For simplicity, we focus on **the extension part of EPIC-KITCHENS-100**.

    The videos are officially hosted on DataBris servers, but the mirrors are slow. Luckily, the extension dataset is also available via AcademicTorrents and HuggingFace, we are going to use the HuggingFace mirror:

    ```bash
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

    **Download the action annotations**

    The action annotations are available in the `epic-kitchens-100-annotations` repository, which we simply clone:

    ```bash
    git clone https://github.com/epic-kitchens/epic-kitchens-100-annotations.git
    ```

    **Verify the folder structure**

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

    **Cut the videos into clips**

    We cut the videos into clips, one for each annotated action. The annotations provide the start and end times of each action, an example annotation looks like this:

    ```text
    narration_id,participant_id,video_id,narration_timestamp,start_timestamp,stop_timestamp,start_frame,stop_frame,narration,verb,verb_class,noun,noun_class,all_nouns,all_noun_classes
    P01_102_0,P01,P01_102,00:00:01.100,00:00:00.54,00:00:02.23,27,111,take knife and plate,take,0,knife,4,"['knife', 'plate']","[4, 2]"
    ```

    We have let an AI assistant write a Python script which loads the annotations from the two files with `pandas`, and then calls `ffmpeg` to cut the clips from the videos. We also downsized the videos to 854x480px.

    You can find [the script](https://huggingface.co/datasets/lightly-ai/epic-kitchens-100-clips/blob/main/cut_clips.py) in the HuggingFace dataset. You can run it as follows, make sure ffmpeg is already installed on your system:

    ```bash
    pip install pandas tqdm
    python cut_clips.py
    ```

    It expects the folder structure described above, and creates a clips folder with the cut clips, named by their narration ID, e.g. `clips/P01/P01_102_0.mp4` for the example annotation above.

    !!! note
        For the 464 GB dataset of videos, the script ran for about 8.5 hours on a 47-core machine, not exhaustively using all cores. It created 37455 clips, with a total size of 24 GB.

## Loading the Clips in LightlyStudio

Go to the downloaded folder and install the dependencies. We use `pandas` for loading annotations and `tqdm` for displaying progress:

```bash
cd epic-kitchens-100-clips
pip install -r requirements.txt
```

All commands below run from this folder, so that the relative paths `./clips` and `./epic-kitchens-100-annotations` resolve correctly.

### Run the Loading Scripts

Run the three scripts from the HuggingFace dataset in order:

```bash
# Add the clips to a new video dataset
python lightly_studio_1_load_videos.py

# Add captions and metadata from the annotation CSVs with bulk inserts
python lightly_studio_2_load_anotations_fast.py

# Start the LightlyStudio GUI
python lightly_studio_3_start_gui.py
```

The first script creates the dataset and computes the embeddings for all clips with the large Perception Encoder model from `embedding_model.py`. This is the slowest step. The second script loads the annotations in bulk, which is much faster than adding them one-by-one. The third script registers the plugin from `caption_similarity_plugin.py` and starts the GUI, so that the plugin is available in the GUI. Run the first script only once, because it creates a new dataset. The data is stored in the `lightly_studio.db` file, so to restart the GUI later, run only `python lightly_studio_3_start_gui.py`.

!!! note "Processing time"
    On a Linux server with an NVIDIA RTX 4090 GPU, the first script takes about 3 hours 45 minutes for the 37455 clips:

    - **Indexing**: about 31 minutes, at 20 clips per second
    - **Embedding**: about 3 hours 15 minutes, at 3.21 clips per second with the large `PE-Core-L14-336` model

    The default tiny model is faster, but gives less satisfactory results. For more information, see the note about the embedding model in [Get a Quick Overview](#get-a-quick-overview).

## Exploring EpicKitchens with LightlyStudio

### Get a Quick Overview

- **Grid**: Shows all 37455 clips with their narrations. Hover over a clip to play it. Double-click a clip to see all metadata from the CSV.
- **Embedding plot**: Shows the clip embeddings from the [Perception Encoder model](https://github.com/facebookresearch/perception_models) in 2D. Similar clips form clusters. Lasso-select a cluster to see its clips in the grid and tag them.
- **Text search**: Finds clips with specific content. LightlyStudio compares the embedding of your text with the clip embeddings and shows a similarity score between 0 and 1 for each clip.

!!! note "Embedding model"
    By default, LightlyStudio embeds videos with the tiny `PE-Core-T16-384` variant of Perception Encoder. For this tutorial, we use the large `PE-Core-L14-336` variant, which the scripts load from `embedding_model.py`. It gives better results for the alignment score between narrations and videos, and for the other workflows that use embeddings. To learn how to use your own model, see [Using Your Own Embeddings](../workflows/embeddings.md#using-your-own-embeddings).

<video autoplay loop muted playsinline controls style="width: 100%;">
  <source src="https://storage.googleapis.com/lightly-public/studio/tutorials/epic-kitchen/epickitchen_overview_full.mp4" type="video/mp4">
</video>

### Understand the Dataset

To learn more about the quality of the dataset, for example how repetitive it is, we can use more of the tools in LightlyStudio.

#### Find Near-Duplicate Clips

First, we look at the embedding plot in more detail. Besides the large clusters, there are many very small clusters. When we lasso-select one of them, we see that it contains very short clips from the same video. The clips show almost the same scene, with only small differences in the action.

These clusters are interesting because they have very low diversity. They can also be a problem: very short clips give little information, and the near-duplicates give the same scene too much weight during training.

<video autoplay loop muted playsinline controls style="width: 100%;">
  <source src="https://storage.googleapis.com/lightly-public/studio/tutorials/epic-kitchen/epickitchen_nearduplicates.m4v" type="video/mp4">
</video>

#### Find Correlations with Metadata

Next, we use the embedding plot to see how the metadata values are distributed. In the embedding plot, use `Color by` and select the `participant_id` metadata field. The colors show that the clusters form mainly by participant. Thus, the clips from one participant are highly correlated: same kitchen, same objects, and similar recordings.

<video autoplay loop muted playsinline controls style="width: 100%;">
  <source src="https://storage.googleapis.com/lightly-public/studio/tutorials/epic-kitchen/epickitchen_emebd_participant_corr.m4v" type="video/mp4">
</video>

#### Find Low-Quality Clips with Text Search

We can also use text search to find clips with bad image quality. For example, search for `dark kitchen` to find clips with bad lighting, or for `blurry video` to find clips with motion blur from fast head movements. Steam from cooking can also make the view blurry. Search for `steam` to find these clips. Tag the results, so that you can examine them later or remove them from the dataset.

<video autoplay loop muted playsinline controls style="width: 100%;">
  <source src="https://storage.googleapis.com/lightly-public/studio/tutorials/epic-kitchen/epickitchen_difficult_text.mp4" type="video/mp4">
</video>

#### Find Mismatches Between Narrations and Videos

An important question when we do QA on narrations is: does the narration describe what happens in the video? To find mismatches, we compare the text embedding of the narration with the video embedding. A low alignment score shows a narration that is ambiguous or does not match the video.

The plugin in `caption_similarity_plugin.py` calculates this alignment score for each clip and stores it as a new metadata field. `lightly_studio_3_start_gui.py` registers the plugin, so you can run it from the plugin menu at the top right of the GUI.

After the plugin runs, sort or filter the clips by the new metadata field to see the clips with the lowest alignment first.

<video autoplay loop muted playsinline controls style="width: 100%;">
  <source src="https://storage.googleapis.com/lightly-public/studio/tutorials/epic-kitchen/epickitchen_cpation_sim.mp4" type="video/mp4">
</video>

Most of the clips with a low score are very short, and the described action is short or ambiguous. For example:

- `pick up fork`, but the person actually cleans the fork while washing the dishes
- `pick up phone`, but there is no phone in the clip

Thus, we find ambiguous and mismatched narrations even in EPIC-KITCHENS-100, a highly curated and widely used dataset. In your own dataset, with auto-generated captions or human narrations, you can expect to find many more of them.

Besides sorting, we can also filter by the alignment score and look at the [dataset distributions](../workflows/dataset_distributions.md) of the clips with a low score. The distribution of the `verb` metadata field shows that some verbs often have a low score, for example `open`, `close`, and `shake`. These verbs are often ambiguous, or they describe only one part of a longer action.

<video autoplay loop muted playsinline controls style="width: 100%;">
  <source src="https://storage.googleapis.com/lightly-public/studio/tutorials/epic-kitchen/epickitchen_distributions.mp4" type="video/mp4">
</video>

## Conclusion

To summarise, we have shown how to:

- Download the preprocessed EPIC-KITCHENS-100 clips and narrations from HuggingFace and load them into LightlyStudio
- Find near-duplicate clips and see that the clips form clusters by participant
- Find low-quality clips, such as dark or blurry clips, with text search
- Find ambiguous and mismatched narrations with the alignment score, and the verbs that cause them most often

Even a highly curated and widely used dataset such as EPIC-KITCHENS-100 has these problems. You can use the same workflow to do QA on your own video dataset, with auto-generated captions or human narrations.

This only scratches the surface of the capabilities of LightlyStudio. To see how to edit captions, export the annotations, and more, check out the rest of this documentation, for example [Add Captions](../workflows/captions.md), [Sampling](../workflows/sampling.md), and [Export](../workflows/export.md).
