---
title: LightlyStudio Glossary
description: Definitions of LightlyStudio dataset, annotation, sampling, and model evaluation terms.
---

# Glossary

Quick reference for the terms and abbreviations used throughout the LightlyStudio documentation.

| Term | Description |
| ---- | ----------- |
| Annotation | A classification, object-detection box, or segmentation mask attached to a sample. Each annotation has an annotation class and an annotation type, and belongs to an annotation source. Can represent ground truth or a model prediction. LightlyStudio uses "annotation" rather than "label" for this concept. See [Annotations](concepts_and_tools/annotations.md). |
| Annotation class | The category assigned to an annotation, such as `dog`, `cat`, or `car`. Not to be confused with annotation type, which describes the form of the annotation. |
| Annotation crop | The image region defined by an annotation's bounding box or mask, extracted as a standalone image. Used to compute per-annotation embeddings. |
| Annotation source | A named group of annotations, such as `ground_truth` or `model_v1`. Keeps annotations from different people, tools, or models separate. Compare with tag, which groups samples rather than annotations. |
| Annotation type | The form of an annotation: classification, object detection, or segmentation. Compare with annotation class, which describes the category. |
| Caption | A text description associated with a sample, for example as training data for a vision-language model. See [Captions](concepts_and_tools/captions.md). |
| Dataset | A collection of samples managed together, including their annotations, captions, embeddings, metadata, and tags. A dataset can be an image dataset or a video dataset. |
| Dataset distribution | A summary of how annotations or metadata values occur across the current view. See [Dataset Distributions](concepts_and_tools/dataset_distributions.md). |
| Embedding plot | An interactive 2D projection of embedding space where each point represents a sample or annotation. See [Embeddings](concepts_and_tools/embeddings.md). |
| Evaluation run | A saved comparison between a ground-truth and a prediction annotation source. Stores configuration, results, a confusion matrix, and per-sample metrics. See [Model Evaluation](concepts_and_tools/evaluation.md). |
| Export | A copy of dataset content saved in a standard format (such as COCO or YOLO) for use outside LightlyStudio. See [Export](concepts_and_tools/export.md). |
| Frame | A still image extracted from a video. LightlyStudio retains its frame number, timestamp, and parent video. Each frame is a sample. See [Video Dataset](dataset_setup/video_dataset.md#frame-grid-view). |
| Image dataset | A dataset whose primary samples are images. See [Image Dataset](dataset_setup/image_dataset.md). |
| Lightly Query Language | SQL-like language used by the GUI query editor to filter images by fields, tags, and annotations. See [LQL reference](concepts_and_tools/lightly_query_language.md). |
| Plugin | An installable extension that adds a workflow to LightlyStudio, such as model-assisted segmentation. See [Plugins](concepts_and_tools/plugins.md). |
| Python API | The classes and functions in the `lightly_studio` package for working with datasets programmatically. See [Dataset API](api/dataset.md). |
| Query | A reusable description of a dataset subset. In Python, a query can filter, sort, and slice samples. In the GUI, it uses Lightly Query Language. See [Query in Python](concepts_and_tools/search_and_filter.md#query-in-python). |
| Sample | An individual data item — an image, a video, or an extracted video frame. Samples are the basic unit of a dataset and can carry annotations, captions, embeddings, metadata, and tags. |
| Sampling | Algorithmic selection of a smaller, more useful subset from a dataset. The result is stored as a tag. See [Sampling](concepts_and_tools/sampling.md). |
| Similarity search | Embedding-based search that ranks samples by visual or semantic similarity to a given input in embedding space. See [Search in the GUI](concepts_and_tools/search_and_filter.md#search-in-gui). |
| Tag | A named marker for organizing samples into reusable groups, such as `reviewed` or `train`. Sampling results are saved as tags. Compare with annotation source, which groups annotations rather than samples. See [Tags](concepts_and_tools/tags.md). |
| Video dataset | A dataset whose primary samples are videos. Supports frame extraction and frame-level annotations. See [Video Dataset](dataset_setup/video_dataset.md). |
| View | A filtered or sorted perspective on a dataset that shows a subset of its samples without modifying the underlying data. Filters and queries produce views. |
