---
title: LightlyStudio FAQ
description: Frequently asked questions about LightlyStudio — price and license, installation, supported data and formats, features, data privacy, and the Python API.
---

# Frequently Asked Questions

Common questions about LightlyStudio. If you do not find your question here,
[ask in Discord](https://discord.com/invite/xvNJW94) or
[open an issue on GitHub](https://github.com/lightly-ai/lightly-studio/issues/new).

## About LightlyStudio and licensing

### What is LightlyStudio?

LightlyStudio is an open-source tool for computer-vision datasets. It brings data curation,
annotation, and management into one app. You load a dataset from a Python script. Then you explore,
curate, annotate, and evaluate it through a browser app. It works with images and videos. It stays
fast on large datasets, up to 2M+ images with embeddings on a single machine (M1, 16 GB RAM).

### How is LightlyStudio different from tools like FiftyOne, Roboflow, or CVAT?

Most tools struggle with large datasets and cover only one part of the loop. Some only
label data, others only explore it. LightlyStudio solves both. It scales to millions of
images on a single machine, embeddings included. And it unifies the whole loop in one
tool: curation, annotation, embedding-based search, sampling, and model evaluation. It is fully
scriptable from Python, runs locally, and is open source under Apache 2.0. For teams,
[LightlyStudio Enterprise](enterprise/index.md) adds collaboration, role-based permissions, and
managed cloud credentials.

### Is LightlyStudio free or paid?

LightlyStudio is free and open source. You can install it and use every feature on your own machine
at no cost. [LightlyStudio Enterprise](enterprise/index.md) is a separate paid product for teams. It
adds collaboration, role-based access, and central credential management. Your team can
[start with it for free](https://app.studio.lightly.ai/auth/signup).

### Is LightlyStudio open source, and what license does it use?

Yes. LightlyStudio is open source under the [Apache License 2.0](https://github.com/lightly-ai/lightly-studio/blob/main/LICENSE).
This license permits commercial use, modification, and distribution. The source is on
[GitHub](https://github.com/lightly-ai/lightly-studio).

### Is there an enterprise edition?

Yes. [LightlyStudio Enterprise](enterprise/index.md) is a server edition for teams. It adds
collaboration, role-based permissions, and managed cloud credentials. We offer it as a fully hosted
service. An on-premise deployment is available at a premium.

## Installation and running

### How do I install and run LightlyStudio?

Install LightlyStudio from PyPI:

```shell
pip install lightly-studio
```

Then index a dataset in a Python script. Call `ls.start_gui()` to start a local server and open the
app at `http://localhost:8001`. For a complete example, see the [quickstart](index.md#quickstart).

### Can I try LightlyStudio without installing anything?

Yes. You can [start a free trial](https://app.studio.lightly.ai/auth/signup) of the fully hosted service.
You can also run LightlyStudio in a hosted notebook such as Google Colab. See
[Run LightlyStudio from a Notebook](get_started/notebooks.md). For a local install, run
`lightly-studio quickstart`. This command downloads an example dataset and opens the app.

### What operating systems and Python versions are supported?

LightlyStudio runs on Windows, Linux, and macOS. It supports Python 3.9 to 3.14. Python 3.10 gives
the best compatibility with plugins such as SAM autolabeling.

### How large a dataset can LightlyStudio handle?

LightlyStudio handles millions of images. In tests, it ran 2M+ images with embeddings on a MacBook
(M1, 16 GB RAM), and it scales beyond that on standard hardware. Its indexing and search use Rust for
speed, and it stays responsive on datasets such as COCO and ImageNet.

## Features and capabilities

### Does LightlyStudio support video annotation?

Yes. LightlyStudio has [video datasets](workflows/video_dataset.md). It extracts frames from a video
and shows them in a frame grid. It supports frame-level annotations.

### Does LightlyStudio do classification, object detection, and segmentation?

Yes. An [annotation](workflows/annotations.md) can be a classification, an object-detection box, or
a segmentation mask, for both ground truth and model predictions.

### Can LightlyStudio auto-label my data?

Yes. [Plugins](ecosystem/plugins.md) add model-assisted labeling, such as SAM autolabeling for
segmentation. You can review and correct the annotations in the annotation editor.

### Can LightlyStudio curate data to reduce labeling cost?

Yes. [Sampling](workflows/sampling.md) selects a smaller, more useful subset of your dataset. For
example, it can select the most diverse or representative samples. You then label fewer images to
reach the same model accuracy.

### Can I search my images by text or visual similarity?

Yes. LightlyStudio computes [embeddings](core_concepts/embeddings.md) on ingest. You can run a text
search, for example "coffee". You can run a visual [similarity search](workflows/search_and_filter.md)
to find related samples. You can also explore clusters in the embedding plot.

### Can I evaluate model predictions against ground truth?

Yes. [Model evaluation](workflows/evaluation.md) compares a prediction annotation source against a
ground-truth annotation source. It produces a confusion matrix and per-sample metrics. These results
help you find failure patterns in your dataset.

### Which embedding models does LightlyStudio use?

By default, LightlyStudio embeds images with MobileCLIP and videos with Perception Encoder. You can
also [use your own embeddings](core_concepts/embeddings.md#using-your-own-embeddings).

## Data and formats

### What data formats can I import and export?

You can import [images](workflows/image_dataset.md#from-a-folder) and
[videos](workflows/video_dataset.md#from-a-folder) from folders or cloud storage. You can also import
[image annotations](workflows/image_dataset.md#from-an-annotation-format) from COCO, YOLO, Pascal VOC,
and the Lightly format, and [video annotations](workflows/video_dataset.md#from-an-annotation-format)
from YouTube-VIS. For any other format, you can attach annotations from Python. You can
[export](workflows/export.md) an entire dataset or a filtered subset to COCO, YOLO, Pascal VOC,
YouTube-VIS, or CSV.

### Can LightlyStudio read data from S3, GCS, or Azure?

Yes. LightlyStudio reads images and videos from Amazon S3, Google Cloud Storage, and Azure Blob
Storage. For setup and limits, see [Using Cloud Storage](ecosystem/cloud_storage.md). The hosted
[LightlyStudio Enterprise](enterprise/index.md) service reads data from cloud storage only; local
folders work with the open-source version.

### Where does LightlyStudio store my data?

Your images and videos stay in their original folder or remote storage. LightlyStudio streams them
into the app for display. It writes only metadata, annotations, and embeddings to a local
`lightly_studio.db` file, which uses DuckDB. The hosted
[LightlyStudio Enterprise](enterprise/index.md) service instead reads your images and videos from
cloud storage and stores this metadata in PostgreSQL.

## Data privacy

### Does my data ever leave my machine?

No. LightlyStudio runs on your own machine. The app, the backend server, and the database are all
local. Your images and datasets never leave your machine.

<!-- TODO(Michal, 09/2026): Uncomment once `RemoteEmbedder` ships.
### Can I use my own embedding model without exposing its weights?

Yes. Serve your model over HTTP with [`lightly-studio-serve`](https://pypi.org/project/lightly-studio-serve/).
LightlyStudio sends images to your local service and gets embeddings back. The model weights never
leave your machine.
-->

### What usage data does LightlyStudio collect, and can I opt out?

LightlyStudio collects anonymous usage analytics. To opt out, set the environment variable
`LIGHTLY_STUDIO_ANALYTICS_ENABLED=false` before you start LightlyStudio. The GUI then loads no
analytics.

## Python API and automation

### Can I script everything from Python?

Yes. You can do everything in LightlyStudio from its [Python API](api/dataset.md). You can index
datasets, query and slice samples, add annotations and tags, run sampling, and start the GUI. Import
it as `import lightly_studio as ls`.

### Is there a command-line interface?

Yes. The `lightly-studio` command has two subcommands. `quickstart` downloads an example dataset and
opens the app. `gui` starts the app on an already-indexed dataset without a reindex.
