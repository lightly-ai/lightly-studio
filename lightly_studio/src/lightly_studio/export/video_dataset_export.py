"""Exports video datasets from Lightly Studio into various formats."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from uuid import UUID

from labelformat.formats.youtubevis import YouTubeVISInstanceSegmentationTrackOutput
from sqlmodel import Session

from lightly_studio.core.video.video_sample import VideoSample
from lightly_studio.export import classification_csv, youtube_vis_label_input
from lightly_studio.type_definitions import PathLike

DEFAULT_EXPORT_FILENAME = "youtube_vis_export.json"
DEFAULT_CLASSIFICATION_EXPORT_FILENAME = "classification_export.csv"


class VideoDatasetExport:
    """Provides methods to export a video dataset or a subset of it."""

    def __init__(self, session: Session, samples: Iterable[VideoSample]):
        """Initialize the export with a database session and the video samples to export."""
        self.session = session
        self.samples = samples

    def to_youtube_vis_segmentation_mask(
        self, output_json: PathLike = DEFAULT_EXPORT_FILENAME
    ) -> None:
        """Export video segmentation mask tracks to YouTube-VIS format JSON file.

        Args:
            output_json: Optional path to the output JSON file. If not provided,
                defaults to "youtube_vis_export.json".
        """
        to_youtube_vis_segmentation_mask(
            session=self.session,
            samples=self.samples,
            output_json=Path(output_json),
        )

    def to_csv_classifications(
        self,
        output_csv: PathLike | None = None,
        annotation_collection_id: UUID | None = None,
    ) -> None:
        """Export whole-video classification annotations to a long-form CSV file.

        Classifications with temporal spans are events and are not included.

        Args:
            output_csv: Destination CSV file. If omitted, defaults to
                ``classification_export.csv`` in the current working directory.
            annotation_collection_id: If provided, only annotations from this annotation
                source are exported. If ``None``, all annotation sources are exported.
        """
        if output_csv is None:
            output_csv = DEFAULT_CLASSIFICATION_EXPORT_FILENAME
        classification_csv.write_classifications_csv(
            samples=self.samples,
            output_csv=Path(output_csv),
            annotation_collection_id=annotation_collection_id,
        )


def to_youtube_vis_segmentation_mask(
    session: Session,
    samples: Iterable[VideoSample],
    output_json: Path,
) -> None:
    """Export video segmentation mask tracks to a YouTube-VIS JSON file."""
    export_input = youtube_vis_label_input.LightlyStudioYouTubeVISInstanceSegmentationTrackInput(
        session=session,
        samples=samples,
    )
    output = YouTubeVISInstanceSegmentationTrackOutput(output_file=output_json)
    output.save(label_input=export_input)
