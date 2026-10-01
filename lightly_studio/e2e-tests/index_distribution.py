"""Index a dataset with configurable content for the distribution panel.

One script for every distribution-panel scenario; env vars toggle what gets
seeded (all default to true):

- ``ADD_CLASSIFICATIONS``   one weighted classification label per image
- ``ADD_OBJECT_DETECTIONS`` a few weighted detection boxes per image
- ``ADD_SEGMENTATIONS``     one or two weighted segmentation masks per image
- ``ADD_METADATA``          numeric metadata fields with distinct distribution
  shapes (bell, flat, skewed, discrete, constant) plus several categorical
  fields (string, boolean, many-valued, partially-missing) — rendered as
  histograms / bar charts in the panel's "Metadata" distribution

Most metadata fields are drawn from a different distribution per comparison
tag, so the panel's "Compare by" selector has something to show. ``confidence``
and ``blur_score`` separate into distinct bells, ``num_defects``, ``location``
and ``weather`` shift their weights, ``camera_id`` narrows far enough to change
the size of the "Other" bucket, ``split`` and ``qa_label`` change how much lands
in "Missing", and ``annotator`` is present only on reviewed samples so it is
entirely missing for a tag that holds none of them. ``brightness``,
``object_size``, ``temperature`` and ``sensor_gain`` are deliberately identical
across tags, as a control for what "no difference between tags" looks like.

Examples::

    make start-e2e-distribution                        # everything
    ADD_METADATA=false make start-e2e-distribution     # annotations only
    ADD_CLASSIFICATIONS=false ADD_OBJECT_DETECTIONS=false \
        ADD_SEGMENTATIONS=false make start-e2e-distribution  # metadata only

Each annotation type uses a distinct, weighted class pool so the bar chart has
a clear shape per selection. Everything is synthetic, so the sole input
required is an images folder. Point it at any images you already have via
``EXAMPLES_IMAGES_PATH`` (defaults to the COCO subset used by
``index_general.py``).

Re-running recreates the dataset: it resets the local database on every run,
since DuckDB has no single-dataset delete.
"""

import random
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import numpy as np
from environs import Env
from numpy.typing import NDArray

import lightly_studio as ls
from lightly_studio.core.annotation.annotation_create import (
    CreateAnnotation,
    CreateClassification,
    CreateObjectDetection,
    CreateSegmentationMask,
)
from lightly_studio.core.image.image_sample import ImageSample
from lightly_studio.database import db_manager
from lightly_studio.resolvers import metadata_resolver

env = Env()
env.read_env()

IMAGES_PATH = env.path("EXAMPLES_IMAGES_PATH", "datasets/coco_subset_128_images/images")

ADD_CLASSIFICATIONS = env.bool("ADD_CLASSIFICATIONS", True)
ADD_OBJECT_DETECTIONS = env.bool("ADD_OBJECT_DETECTIONS", True)
ADD_SEGMENTATIONS = env.bool("ADD_SEGMENTATIONS", True)
ADD_METADATA = env.bool("ADD_METADATA", True)

DATASET_NAME = "distribution_example_dataset"
RANDOM_SEED = 42

COMPARISON_TAG_REVIEWED = "distribution_reviewed"
COMPARISON_TAG_PRIORITY = "distribution_priority"
COMPARISON_TAG_EMPTY = "distribution_empty"

# How many samples each comparison tag covers. The two ranges overlap on
# [PRIORITY_TAG_START, REVIEWED_TAG_END) so the panel has to handle a sample
# that belongs to both tags.
REVIEWED_TAG_END = 32
PRIORITY_TAG_START = 16
PRIORITY_TAG_END = 48

# Distinct, weighted class pools per type so each distribution has a clear shape.
CLASSIFICATION_CLASSES = ["daytime", "night", "dawn", "dusk", "indoor"]
CLASSIFICATION_WEIGHTS = [0.45, 0.25, 0.15, 0.1, 0.05]

DETECTION_CLASSES = ["car", "person", "bicycle", "traffic_light", "bus", "truck"]
DETECTION_WEIGHTS = [0.35, 0.3, 0.12, 0.1, 0.08, 0.05]

SEGMENTATION_CLASSES = ["road", "sky", "building", "vegetation", "sidewalk"]
SEGMENTATION_WEIGHTS = [0.3, 0.25, 0.2, 0.15, 0.1]

LOCATIONS = ["city", "rural", "mountain", "coastal", "desert"]
WEATHER_CONDITIONS = ["sunny", "partly_cloudy", "overcast", "rainy", "foggy", "snowy"]
DEFECT_COUNTS = [0, 1, 2, 3, 5, 8]

# Common ML split assignment. Every profile leaves some samples unassigned, at a
# rate that differs per tag, so the "Missing" bucket is a different size in each
# compared series.
DATASET_SPLITS = ["train", "val", "test"]
SPLIT_WEIGHTS = [0.70, 0.20, 0.10]

# 25 camera IDs: exercises the top-20 "Other" bucket in value-counts.
CAMERA_IDS = [f"CAM_{i:02d}" for i in range(1, 26)]
# CAM_01 most frequent, with a long tail that keeps "Other" large.
BROAD_CAMERA_WEIGHTS = [max(1, 26 - i) for i in range(1, 26)]
# Priority work comes off a handful of cameras, so its "Other" bucket is small.
FOCUSED_CAMERA_COUNT = 4
FOCUSED_CAMERA_WEIGHTS = [20 if i <= FOCUSED_CAMERA_COUNT else 1 for i in range(1, 26)]

# Only reviewed samples carry an annotator, so the field is entirely "Missing"
# for a tag that holds none of them.
ANNOTATORS = ["alice", "bob", "carol", "dan"]

# Free-form QA label. It has more than 20 distinct values, so value-counts folds
# its tail into an "Other" bucket, two of its literal values are spelled
# "Missing" and "Other" — the same names as the synthetic buckets — and the field
# is absent on some samples. That combination is what the panel has to keep apart
# when it aligns categories across tag series.
QA_LABELS = ["approved", "rejected", "pending", "Missing", "Other"] + [
    f"batch_{index:02d}" for index in range(1, 20)
]
QA_LABEL_WEIGHTS = [12, 8, 6, 5, 5] + [1] * 19

BLUR_SCORE_STDEV = 0.10


@dataclass(frozen=True)
class MetadataProfile:
    """How the tag-dependent metadata fields are drawn for one population.

    Attributes:
        confidence_mean: Mean of the ``confidence`` bell.
        confidence_stdev: Standard deviation of the ``confidence`` bell.
        blur_mean: Mean of the ``blur_score`` bell.
        defect_weights: Weights over ``DEFECT_COUNTS``.
        location_weights: Weights over ``LOCATIONS``.
        weather_weights: Weights over ``WEATHER_CONDITIONS``.
        camera_weights: Weights over ``CAMERA_IDS``.
        reviewed_probability: Probability that ``reviewed`` is true.
        split_missing_probability: Probability that ``split`` is absent.
        qa_label_missing_probability: Probability that ``qa_label`` is absent.
        has_annotator: Whether ``annotator`` is set at all.
    """

    confidence_mean: float
    confidence_stdev: float
    blur_mean: float
    defect_weights: Sequence[float]
    location_weights: Sequence[float]
    weather_weights: Sequence[float]
    camera_weights: Sequence[float]
    reviewed_probability: float
    split_missing_probability: float
    qa_label_missing_probability: float
    has_annotator: bool


# The untagged bulk of the dataset.
BASELINE_PROFILE = MetadataProfile(
    confidence_mean=0.75,
    confidence_stdev=0.12,
    blur_mean=0.30,
    defect_weights=[50, 25, 12, 7, 4, 2],
    location_weights=[0.35, 0.25, 0.20, 0.12, 0.08],
    weather_weights=[0.40, 0.25, 0.15, 0.10, 0.07, 0.03],
    camera_weights=BROAD_CAMERA_WEIGHTS,
    reviewed_probability=0.15,
    split_missing_probability=0.20,
    qa_label_missing_probability=0.15,
    has_annotator=False,
)

# Reviewed-only samples are the clean ones: confident, sharp, few defects.
REVIEWED_PROFILE = MetadataProfile(
    confidence_mean=0.90,
    confidence_stdev=0.05,
    blur_mean=0.12,
    defect_weights=[70, 20, 6, 2, 1, 1],
    location_weights=[0.55, 0.25, 0.10, 0.07, 0.03],
    weather_weights=[0.60, 0.25, 0.10, 0.03, 0.01, 0.01],
    camera_weights=BROAD_CAMERA_WEIGHTS,
    reviewed_probability=0.95,
    split_missing_probability=0.05,
    qa_label_missing_probability=0.05,
    has_annotator=True,
)

# Priority-only samples are the problem cases: low confidence, blurry, defective,
# shot in bad weather off a handful of cameras, and poorly labelled.
PRIORITY_PROFILE = MetadataProfile(
    confidence_mean=0.45,
    confidence_stdev=0.15,
    blur_mean=0.70,
    defect_weights=[5, 10, 20, 25, 25, 15],
    location_weights=[0.10, 0.15, 0.35, 0.15, 0.25],
    weather_weights=[0.05, 0.10, 0.20, 0.30, 0.20, 0.15],
    camera_weights=FOCUSED_CAMERA_WEIGHTS,
    reviewed_probability=0.10,
    split_missing_probability=0.45,
    qa_label_missing_probability=0.35,
    has_annotator=False,
)

# The overlap: problem cases that have already been reviewed. It gets its own
# profile so all three populations stay visible instead of one hiding inside
# another when both tags are compared.
REVIEWED_PRIORITY_PROFILE = MetadataProfile(
    confidence_mean=0.65,
    confidence_stdev=0.08,
    blur_mean=0.45,
    defect_weights=[20, 30, 25, 15, 7, 3],
    location_weights=[0.30, 0.20, 0.25, 0.15, 0.10],
    weather_weights=[0.20, 0.25, 0.25, 0.20, 0.07, 0.03],
    camera_weights=FOCUSED_CAMERA_WEIGHTS,
    reviewed_probability=0.90,
    split_missing_probability=0.15,
    qa_label_missing_probability=0.10,
    has_annotator=True,
)

PROFILES_BY_TAGS: Mapping[frozenset[str], MetadataProfile] = {
    frozenset(): BASELINE_PROFILE,
    frozenset({COMPARISON_TAG_REVIEWED}): REVIEWED_PROFILE,
    frozenset({COMPARISON_TAG_PRIORITY}): PRIORITY_PROFILE,
    frozenset({COMPARISON_TAG_REVIEWED, COMPARISON_TAG_PRIORITY}): REVIEWED_PRIORITY_PROFILE,
}


def _box(
    width: int, height: int, left_fraction: float, top_fraction: float
) -> tuple[int, int, int, int]:
    """Return an (x, y, w, h) box covering roughly a third of the image."""
    x = int(width * left_fraction)
    y = int(height * top_fraction)
    return x, y, min(max(1, width // 3), width - x), min(max(1, height // 3), height - y)


def _rectangle_mask(
    width: int, height: int, left_fraction: float, top_fraction: float
) -> NDArray[np.int_]:
    """Return a binary mask (height x width) with a filled rectangle."""
    x, y, w, h = _box(width, height, left_fraction, top_fraction)
    mask = np.zeros((height, width), dtype=np.int_)
    mask[y : y + h, x : x + w] = 1
    return mask


def _add_comparison_tags(samples: Sequence[ImageSample]) -> dict[UUID, frozenset[str]]:
    """Tag the comparison ranges and report which tags each sample ended up with.

    Tagging and the metadata profiles are both driven off this one list, so a
    sample's tags and the distribution its metadata was drawn from can never
    drift apart.

    Args:
        samples: All samples in the dataset, in a stable order.

    Returns:
        The comparison tags per sample ID. Untagged samples are absent.
    """
    tags_by_sample_id: dict[UUID, set[str]] = defaultdict(set)
    for sample in samples[:REVIEWED_TAG_END]:
        sample.add_tag(COMPARISON_TAG_REVIEWED)
        tags_by_sample_id[sample.sample_id].add(COMPARISON_TAG_REVIEWED)
    for sample in samples[PRIORITY_TAG_START:PRIORITY_TAG_END]:
        sample.add_tag(COMPARISON_TAG_PRIORITY)
        tags_by_sample_id[sample.sample_id].add(COMPARISON_TAG_PRIORITY)
    return {sample_id: frozenset(tags) for sample_id, tags in tags_by_sample_id.items()}


def _sample_metadata(rng: random.Random, profile: MetadataProfile) -> Mapping[str, Any]:
    """Return one sample's metadata, drawn from its comparison-tag profile.

    Numeric fields cover distinct distribution shapes (bell, flat, skewed,
    discrete, constant) and categorical fields exercise weighted strings, a
    boolean, a many-valued field that triggers the "Other" bucket, and
    partially-missing fields that trigger the "Missing" bucket.

    Everything drawn from ``profile`` differs per comparison tag, so selecting
    tags in the panel produces visibly different series. ``brightness``,
    ``object_size``, ``temperature`` and ``sensor_gain`` are the same for every
    profile on purpose: they are the control for what no difference looks like.

    Args:
        rng: Seeded random source.
        profile: Profile for this sample's comparison-tag membership.

    Returns:
        The metadata for one sample.
    """
    metadata: dict[str, Any] = {
        # Numeric, tag-dependent.
        "confidence": _clamped_gauss(
            rng, mean=profile.confidence_mean, stdev=profile.confidence_stdev
        ),
        "blur_score": _clamped_gauss(rng, mean=profile.blur_mean, stdev=BLUR_SCORE_STDEV),
        "num_defects": rng.choices(DEFECT_COUNTS, profile.defect_weights)[0],
        # Numeric, identical across tags.
        "brightness": rng.uniform(0.0, 255.0),
        "object_size": rng.lognormvariate(3.0, 0.8),
        "temperature": rng.randint(10, 40),
        "sensor_gain": 1.0,
        # Categorical, tag-dependent.
        "location": rng.choices(LOCATIONS, profile.location_weights)[0],
        "weather": rng.choices(WEATHER_CONDITIONS, profile.weather_weights)[0],
        "reviewed": rng.random() < profile.reviewed_probability,
        "camera_id": rng.choices(CAMERA_IDS, profile.camera_weights)[0],
    }
    if rng.random() >= profile.split_missing_probability:
        metadata["split"] = rng.choices(DATASET_SPLITS, SPLIT_WEIGHTS)[0]
    if rng.random() >= profile.qa_label_missing_probability:
        metadata["qa_label"] = rng.choices(QA_LABELS, QA_LABEL_WEIGHTS)[0]
    if profile.has_annotator:
        metadata["annotator"] = rng.choice(ANNOTATORS)
    return metadata


def _clamped_gauss(rng: random.Random, mean: float, stdev: float) -> float:
    """Return a normal sample clamped to [0, 1]."""
    return min(1.0, max(0.0, rng.gauss(mean, stdev)))


def main() -> None:
    """Create the dataset, seed the configured content, and launch the UI."""
    db_manager.connect(db_file="lightly_studio.db", cleanup_existing=True)

    dataset = ls.ImageDataset.create(name=DATASET_NAME)
    dataset.add_images_from_path(path=IMAGES_PATH)
    samples = list(dataset)
    rng = random.Random(RANDOM_SEED)

    tags_by_sample_id = _add_comparison_tags(samples)
    dataset.query()[:0].add_tag(COMPARISON_TAG_EMPTY)

    for sample in samples:
        annotations: list[CreateAnnotation] = []

        if ADD_CLASSIFICATIONS:
            annotations.append(
                CreateClassification(
                    class_name=rng.choices(CLASSIFICATION_CLASSES, CLASSIFICATION_WEIGHTS)[0],
                    confidence=rng.uniform(0.6, 1.0),
                )
            )

        if ADD_OBJECT_DETECTIONS:
            for _ in range(rng.randint(1, 4)):
                x, y, w, h = _box(
                    sample.width, sample.height, rng.uniform(0.05, 0.6), rng.uniform(0.05, 0.6)
                )
                annotations.append(
                    CreateObjectDetection(
                        class_name=rng.choices(DETECTION_CLASSES, DETECTION_WEIGHTS)[0],
                        x=x,
                        y=y,
                        width=w,
                        height=h,
                        confidence=rng.uniform(0.5, 1.0),
                    )
                )

        if ADD_SEGMENTATIONS:
            for _ in range(rng.randint(1, 2)):
                annotations.append(
                    CreateSegmentationMask.from_binary_mask(
                        class_name=rng.choices(SEGMENTATION_CLASSES, SEGMENTATION_WEIGHTS)[0],
                        binary_mask=_rectangle_mask(
                            sample.width,
                            sample.height,
                            rng.uniform(0.05, 0.5),
                            rng.uniform(0.05, 0.5),
                        ),
                        confidence=rng.uniform(0.5, 1.0),
                    )
                )

        if annotations:
            sample.add_annotations(annotations=annotations)

    if ADD_METADATA:
        sample_metadata: list[tuple[UUID, Mapping[str, Any]]] = [
            (
                sample.sample_id,
                _sample_metadata(
                    rng,
                    PROFILES_BY_TAGS[tags_by_sample_id.get(sample.sample_id, frozenset())],
                ),
            )
            for sample in samples
        ]
        metadata_resolver.bulk_update_metadata(db_manager.persistent_session(), sample_metadata)

    seeded = [
        name
        for name, enabled in [
            ("classifications", ADD_CLASSIFICATIONS),
            ("object detections", ADD_OBJECT_DETECTIONS),
            ("segmentation masks", ADD_SEGMENTATIONS),
            ("metadata", ADD_METADATA),
        ]
        if enabled
    ]
    print(
        f"Created dataset '{DATASET_NAME}' with {len(samples)} images and "
        f"{', '.join(seeded) if seeded else 'no extra content'}."
    )
    ls.start_gui()


if __name__ == "__main__":
    main()
