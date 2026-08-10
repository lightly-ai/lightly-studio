"""Export image classification annotations to CSV."""

from __future__ import annotations

import csv
from collections.abc import Iterable
from pathlib import Path
from uuid import UUID

from lightly_studio.core.image.image_sample import ImageSample
from lightly_studio.models.annotation.annotation_base import AnnotationType

CSV_FIELDNAMES = (
    "file_path_abs",
    "class_name",
    "confidence",
    "annotation_source",
)


def write_classifications_csv(
    samples: Iterable[ImageSample],
    output_csv: Path,
    annotation_collection_id: UUID | None,
) -> None:
    """Write image classification annotations as long-form CSV.

    Args:
        samples: Image samples whose classifications are exported.
        output_csv: Destination CSV file.
        annotation_collection_id: If provided, only annotations from this annotation
            collection are exported. If ``None``, all annotation sources are exported.
    """
    with output_csv.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()
        for sample in samples:
            for annotation in sample.sample_table.annotations:
                if annotation.annotation_type != AnnotationType.CLASSIFICATION:
                    continue
                if (
                    annotation_collection_id is not None
                    and annotation.annotation_collection_id != annotation_collection_id
                ):
                    continue
                writer.writerow(
                    {
                        "file_path_abs": sample.file_path_abs,
                        "class_name": annotation.annotation_label.annotation_label_name,
                        "confidence": annotation.confidence,
                        "annotation_source": annotation.sample.collection.name,
                    }
                )
