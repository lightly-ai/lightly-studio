"""Delete dataset resolver for collections."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, delete, select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.annotation.object_detection import (
    ObjectDetectionAnnotationTable,
)
from lightly_studio.models.annotation.object_track import ObjectTrackTable
from lightly_studio.models.annotation.segmentation import SegmentationAnnotationTable
from lightly_studio.models.annotation_collection import AnnotationCollectionTable
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.caption import CaptionTable
from lightly_studio.models.collection import CollectionTable
from lightly_studio.models.dataset import DatasetTable
from lightly_studio.models.embedding_model import EmbeddingModelTable
from lightly_studio.models.evaluation_annotation_result import EvaluationAnnotationResultTable
from lightly_studio.models.evaluation_result import EvaluationResultTable
from lightly_studio.models.evaluation_result_sample import EvaluationResultSampleTable
from lightly_studio.models.evaluation_sample_metric import EvaluationSampleMetricTable
from lightly_studio.models.group import GroupTable, SampleGroupLinkTable
from lightly_studio.models.image import ImageTable
from lightly_studio.models.metadata import SampleMetadataTable
from lightly_studio.models.sample import SampleTable, SampleTagLinkTable
from lightly_studio.models.sample_embedding import SampleEmbeddingTable
from lightly_studio.models.tag import TagTable
from lightly_studio.models.video import VideoFrameTable, VideoTable
from lightly_studio.resolvers import dataset_resolver
from lightly_studio.resolvers.dataset_resolver import table_coverage_utils


def delete_dataset(
    session: Session,
    dataset_id: UUID,
) -> None:
    """Delete a dataset with all related entities.

    This performs a complete delete of a dataset, removing all associated samples, tags,
    annotations, embeddings, metadata, etc.

    Args:
        session: Database session.
        dataset_id: Dataset ID to delete.
    """
    # Ensure all tables are handled - fails if new tables were added without updating this function.
    table_coverage_utils.verify_table_coverage()

    # Get the hierarchy and collect all IDs.
    hierarchy = dataset_resolver.get_hierarchy(session=session, dataset_id=dataset_id)
    collection_ids = [coll.collection_id for coll in hierarchy]

    # Collect all sample IDs from all collections.
    sample_ids = _get_sample_ids(session=session, collection_ids=collection_ids)

    # Delete in order.
    # DuckDB requires commits (not just flushes) before deleting a table whose
    # FK children were just deleted.
    # The delete phases are grouped as to reduce the number of needed commits.

    # 1. Delete all tables that reference annotation_base.
    _delete_object_detection_annotations(session=session, sample_ids=sample_ids)
    _delete_segmentation_annotations(session=session, sample_ids=sample_ids)
    session.commit()  # Commit before deleting annotation_base.

    # 2. Delete annotation_base and tables that reference sample type tables.
    _delete_annotation_base(session=session, sample_ids=sample_ids)
    _delete_sample_tag_links(session=session, sample_ids=sample_ids)
    _delete_sample_group_links(session=session, sample_ids=sample_ids)
    # Required before deleting groups (SampleGroupLinkTable.parent_sample_id -> GroupTable).
    session.commit()

    # 3. Delete sample attachments.
    _delete_sample_embeddings(session=session, sample_ids=sample_ids)
    _delete_sample_metadata(session=session, sample_ids=sample_ids)
    _delete_captions(session=session, sample_ids=sample_ids)
    _delete_video_frames(session=session, sample_ids=sample_ids)
    # Required before deleting videos (VideoFrameTable.parent_sample_id -> VideoTable).
    session.commit()

    # 4. Delete sample type tables.
    _delete_groups(session=session, sample_ids=sample_ids)
    _delete_videos(session=session, sample_ids=sample_ids)
    _delete_images(session=session, sample_ids=sample_ids)
    session.commit()  # Required before deleting samples.

    # 5. Delete samples and collection-scoped entities.
    _delete_samples(session=session, sample_ids=sample_ids)
    _delete_annotation_labels(session=session, dataset_id=dataset_id)
    _delete_tags(session=session, collection_ids=collection_ids)
    _delete_embedding_models(session=session, collection_ids=collection_ids)
    _delete_object_tracks(session=session, dataset_id=dataset_id)
    session.commit()  # Required before deleting collections.

    # 6. Delete evaluation tables (must come before annotation_collection and dataset).
    _delete_evaluation_sub_tables(session=session, dataset_id=dataset_id)
    _delete_evaluation_results(session=session, dataset_id=dataset_id)
    _delete_annotation_collections(session=session, dataset_id=dataset_id)
    session.commit()

    # 7. Delete collections (with individual commits due to self-referential FKs).
    _delete_collections(session=session, collection_ids=collection_ids)

    # 8. Delete the dataset entry itself.
    _delete_dataset(session=session, dataset_id=dataset_id)
    session.commit()


def _get_sample_ids(session: Session, collection_ids: list[UUID]) -> list[UUID]:
    """Get all sample IDs from the given collections."""
    if not collection_ids:
        return []
    samples = session.exec(
        select(SampleTable.sample_id).where(col(SampleTable.collection_id).in_(collection_ids))
    ).all()
    return list(samples)


def _delete_sample_tag_links(session: Session, sample_ids: list[UUID]) -> None:
    """Delete sample-tag links for the given samples."""
    if not sample_ids:
        return
    session.exec(
        delete(SampleTagLinkTable).where(col(SampleTagLinkTable.sample_id).in_(sample_ids))
    )


def _delete_sample_group_links(session: Session, sample_ids: list[UUID]) -> None:
    """Delete sample-group links for the given samples."""
    if not sample_ids:
        return
    session.exec(
        delete(SampleGroupLinkTable).where(col(SampleGroupLinkTable.sample_id).in_(sample_ids))
    )


def _delete_sample_embeddings(session: Session, sample_ids: list[UUID]) -> None:
    """Delete sample embeddings for the given samples."""
    if not sample_ids:
        return
    session.exec(
        delete(SampleEmbeddingTable).where(col(SampleEmbeddingTable.sample_id).in_(sample_ids))
    )


def _delete_sample_metadata(session: Session, sample_ids: list[UUID]) -> None:
    """Delete sample metadata for the given samples."""
    if not sample_ids:
        return
    session.exec(
        delete(SampleMetadataTable).where(col(SampleMetadataTable.sample_id).in_(sample_ids))
    )


def _delete_object_detection_annotations(session: Session, sample_ids: list[UUID]) -> None:
    """Delete object detection annotation details."""
    if not sample_ids:
        return
    session.exec(
        delete(ObjectDetectionAnnotationTable).where(
            col(ObjectDetectionAnnotationTable.sample_id).in_(sample_ids)
        )
    )


def _delete_segmentation_annotations(session: Session, sample_ids: list[UUID]) -> None:
    """Delete segmentation annotation details."""
    if not sample_ids:
        return
    session.exec(
        delete(SegmentationAnnotationTable).where(
            col(SegmentationAnnotationTable.sample_id).in_(sample_ids)
        )
    )


def _delete_annotation_base(session: Session, sample_ids: list[UUID]) -> None:
    """Delete annotation base records."""
    if not sample_ids:
        return
    session.exec(
        delete(AnnotationBaseTable).where(col(AnnotationBaseTable.sample_id).in_(sample_ids))
    )


def _delete_object_tracks(session: Session, dataset_id: UUID) -> None:
    """Delete object tracks for the given dataset."""
    session.exec(delete(ObjectTrackTable).where(col(ObjectTrackTable.dataset_id) == dataset_id))


def _delete_captions(session: Session, sample_ids: list[UUID]) -> None:
    """Delete captions."""
    if not sample_ids:
        return
    session.exec(delete(CaptionTable).where(col(CaptionTable.sample_id).in_(sample_ids)))


def _delete_video_frames(session: Session, sample_ids: list[UUID]) -> None:
    """Delete video frames."""
    if not sample_ids:
        return
    session.exec(delete(VideoFrameTable).where(col(VideoFrameTable.sample_id).in_(sample_ids)))


def _delete_groups(session: Session, sample_ids: list[UUID]) -> None:
    """Delete group records."""
    if not sample_ids:
        return
    session.exec(delete(GroupTable).where(col(GroupTable.sample_id).in_(sample_ids)))


def _delete_videos(session: Session, sample_ids: list[UUID]) -> None:
    """Delete videos."""
    if not sample_ids:
        return
    session.exec(delete(VideoTable).where(col(VideoTable.sample_id).in_(sample_ids)))


def _delete_images(session: Session, sample_ids: list[UUID]) -> None:
    """Delete images."""
    if not sample_ids:
        return
    session.exec(delete(ImageTable).where(col(ImageTable.sample_id).in_(sample_ids)))


def _delete_samples(session: Session, sample_ids: list[UUID]) -> None:
    """Delete samples."""
    if not sample_ids:
        return
    session.exec(delete(SampleTable).where(col(SampleTable.sample_id).in_(sample_ids)))


def _delete_annotation_labels(session: Session, dataset_id: UUID) -> None:
    """Delete annotation labels for the dataset."""
    session.exec(
        delete(AnnotationLabelTable).where(col(AnnotationLabelTable.dataset_id) == dataset_id)
    )


def _delete_dataset(session: Session, dataset_id: UUID) -> None:
    """Delete the dataset record from DatasetTable."""
    session.exec(delete(DatasetTable).where(col(DatasetTable.dataset_id) == dataset_id))


def _delete_tags(session: Session, collection_ids: list[UUID]) -> None:
    """Delete tags for the given collections."""
    if not collection_ids:
        return
    session.exec(delete(TagTable).where(col(TagTable.collection_id).in_(collection_ids)))


def _delete_embedding_models(session: Session, collection_ids: list[UUID]) -> None:
    """Delete embedding models for the given collections."""
    if not collection_ids:
        return
    session.exec(
        delete(EmbeddingModelTable).where(
            col(EmbeddingModelTable.collection_id).in_(collection_ids)
        )
    )


def _delete_evaluation_sub_tables(session: Session, dataset_id: UUID) -> None:
    """Delete evaluation sub-table rows (metrics, results, sample lists) for the dataset."""
    eval_ids = list(
        session.exec(
            select(EvaluationResultTable.id).where(
                col(EvaluationResultTable.dataset_id) == dataset_id
            )
        ).all()
    )
    if not eval_ids:
        return
    session.exec(
        delete(EvaluationAnnotationResultTable).where(
            col(EvaluationAnnotationResultTable.evaluation_result_id).in_(eval_ids)
        )
    )
    session.exec(
        delete(EvaluationSampleMetricTable).where(
            col(EvaluationSampleMetricTable.evaluation_result_id).in_(eval_ids)
        )
    )
    session.exec(
        delete(EvaluationResultSampleTable).where(
            col(EvaluationResultSampleTable.evaluation_result_id).in_(eval_ids)
        )
    )


def _delete_evaluation_results(session: Session, dataset_id: UUID) -> None:
    """Delete evaluation result rows for the dataset."""
    session.exec(
        delete(EvaluationResultTable).where(
            col(EvaluationResultTable.dataset_id) == dataset_id
        )
    )


def _delete_annotation_collections(session: Session, dataset_id: UUID) -> None:
    """Delete annotation collection rows for the dataset."""
    session.exec(
        delete(AnnotationCollectionTable).where(
            col(AnnotationCollectionTable.dataset_id) == dataset_id
        )
    )


def _delete_collections(session: Session, collection_ids: list[UUID]) -> None:
    """Delete collections in reverse order (children first)."""
    if not collection_ids:
        return
    # Reverse the list to delete children before parents
    for collection_id in reversed(collection_ids):
        session.exec(
            delete(CollectionTable).where(col(CollectionTable.collection_id) == collection_id)
        )
        session.commit()
