"""Loading options for image details."""

from sqlalchemy.orm import defaultload, selectinload
from sqlalchemy.orm.interfaces import LoaderOption

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.annotation.object_track import ObjectTrackTable
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable


def annotation_detail_load_options() -> LoaderOption:
    """Load annotation details in batches for one image."""
    return (
        defaultload(ImageTable.sample)
        .defaultload(SampleTable.annotations)
        .options(
            selectinload(AnnotationBaseTable.annotation_label),
            selectinload(AnnotationBaseTable.object_detection_details),
            selectinload(AnnotationBaseTable.segmentation_details),
            selectinload(AnnotationBaseTable.polygon_details),
            selectinload(AnnotationBaseTable.cuboid_3d_details),
            defaultload(AnnotationBaseTable.object_track).selectinload(
                ObjectTrackTable.parent_object_track
            ),
            selectinload(AnnotationBaseTable.sample).selectinload(SampleTable.tags),
        )
    )
