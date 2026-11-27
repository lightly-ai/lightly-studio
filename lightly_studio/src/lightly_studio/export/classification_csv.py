"""Export classification annotations to CSV."""

from __future__ import annotations

import csv
from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import UUID

from sqlmodel import Session

from lightly_studio.export import annotation_batches
from lightly_studio.models.annotation.annotation_base import AnnotationType

if TYPE_CHECKING:
    from lightly_studio.core.image.image_sample import ImageSample
    from lightly_studio.core.video.video_sample import VideoSample

CSV_FIELDNAMES = (
    "file_path_abs",
    "class_name",
    "confidence",
    "annotation_source",
)


def write_classifications_csv(
    session: Session,
    samples: Iterable[ImageSample | VideoSample],
    output_csv: Path,
    annotation_collection_id: UUID | None,
) -> None:
    """Write whole-sample classification annotations as long-form CSV.

    Args:
        session: The database session.
        samples: Image or video samples whose classifications are exported.
        output_csv: Destination CSV file.
        annotation_collection_id: If provided, only annotations from this annotation
            collection are exported. If ``None``, all annotation sources are exported.
    """
    with output_csv.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()
        for sample, annotations in annotation_batches.iter_sample_annotations(
            session=session,
            samples=samples,
            annotation_types=[AnnotationType.CLASSIFICATION],
            annotation_collection_id=annotation_collection_id,
        ):
            for annotation in annotations:
                # TODO(Igor, 08/2026): Add support for exporting temporal spans.
                if annotation.temporal_span_details is not None:
                    continue
                writer.writerow(
                    {
                        "file_path_abs": sample.file_path_abs,
                        "class_name": annotation.annotation_label.annotation_label_name,
                        "confidence": annotation.confidence,
                        "annotation_source": annotation.sample.collection.name,
                    }
                )
