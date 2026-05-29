"""Delete dataset resolver for collections."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlmodel import Session, SQLModel, col, delete, select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.annotation.object_detection import (
    ObjectDetectionAnnotationTable,
)
from lightly_studio.models.annotation.object_track import ObjectTrackTable
from lightly_studio.models.annotation.segmentation import SegmentationAnnotationTable
from lightly_studio.models.annotation_collection_coverage import (
    AnnotationCollectionCoverageTable,
)
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.caption import CaptionTable
from lightly_studio.models.collection import CollectionTable
from lightly_studio.models.dataset import DatasetTable
from lightly_studio.models.embedding_model import EmbeddingModelTable
from lightly_studio.models.evaluation_annotation_metric import EvaluationAnnotationMetricTable
from lightly_studio.models.evaluation_run import EvaluationRunTable
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
from lightly_studio.utils import batching


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
    _delete_evaluation_sample_metrics(session=session, dataset_id=dataset_id)
    _delete_evaluation_annotation_metrics(session=session, dataset_id=dataset_id)
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
    _delete_annotation_collection_coverage(session=session, collection_ids=collection_ids)
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
    _delete_evaluation_runs(session=session, dataset_id=dataset_id)
    session.commit()  # Required before deleting collections.

    # 6. Delete collections (with individual commits due to self-referential FKs).
    _delete_collections(session=session, collection_ids=collection_ids)

    # 7. Delete the dataset entry itself.
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


def _delete_where_column_in(
    session: Session,
    table: type[SQLModel],
    column: Any,
    values: list[UUID],
) -> None:
    """Delete rows of ``table`` where ``column`` is in ``values``, in batches.

    The id list is chunked so the bind-parameter count of any single statement
    stays well below PostgreSQL's 65,535 limit. All statements run in the
    caller's open transaction; the caller is responsible for committing, which
    keeps the foreign-key-ordering phases in ``delete_dataset`` intact.
    """
    if not values:
        return
    for batch in batching.batched(values, batching.IN_CLAUSE_BATCH_SIZE):
        session.exec(delete(table).where(col(column).in_(batch)))


def _delete_sample_tag_links(session: Session, sample_ids: list[UUID]) -> None:
    """Delete sample-tag links for the given samples."""
    _delete_where_column_in(session, SampleTagLinkTable, SampleTagLinkTable.sample_id, sample_ids)


def _delete_sample_group_links(session: Session, sample_ids: list[UUID]) -> None:
    """Delete sample-group links for the given samples."""
    _delete_where_column_in(
        session, SampleGroupLinkTable, SampleGroupLinkTable.sample_id, sample_ids
    )


def _delete_sample_embeddings(session: Session, sample_ids: list[UUID]) -> None:
    """Delete sample embeddings for the given samples."""
    _delete_where_column_in(
        session, SampleEmbeddingTable, SampleEmbeddingTable.sample_id, sample_ids
    )


def _delete_sample_metadata(session: Session, sample_ids: list[UUID]) -> None:
    """Delete sample metadata for the given samples."""
    _delete_where_column_in(session, SampleMetadataTable, SampleMetadataTable.sample_id, sample_ids)


def _delete_object_detection_annotations(session: Session, sample_ids: list[UUID]) -> None:
    """Delete object detection annotation details."""
    _delete_where_column_in(
        session,
        ObjectDetectionAnnotationTable,
        ObjectDetectionAnnotationTable.sample_id,
        sample_ids,
    )


def _delete_segmentation_annotations(session: Session, sample_ids: list[UUID]) -> None:
    """Delete segmentation annotation details."""
    _delete_where_column_in(
        session, SegmentationAnnotationTable, SegmentationAnnotationTable.sample_id, sample_ids
    )


def _delete_annotation_base(session: Session, sample_ids: list[UUID]) -> None:
    """Delete annotation base records."""
    _delete_where_column_in(session, AnnotationBaseTable, AnnotationBaseTable.sample_id, sample_ids)


def _delete_annotation_collection_coverage(session: Session, collection_ids: list[UUID]) -> None:
    """Delete annotation collection coverage rows scoped to the dataset's collections."""
    _delete_where_column_in(
        session,
        AnnotationCollectionCoverageTable,
        AnnotationCollectionCoverageTable.annotation_collection_id,
        collection_ids,
    )


def _delete_object_tracks(session: Session, dataset_id: UUID) -> None:
    """Delete object tracks for the given dataset."""
    session.exec(delete(ObjectTrackTable).where(col(ObjectTrackTable.dataset_id) == dataset_id))


def _delete_captions(session: Session, sample_ids: list[UUID]) -> None:
    """Delete captions."""
    _delete_where_column_in(session, CaptionTable, CaptionTable.sample_id, sample_ids)


def _delete_video_frames(session: Session, sample_ids: list[UUID]) -> None:
    """Delete video frames."""
    _delete_where_column_in(session, VideoFrameTable, VideoFrameTable.sample_id, sample_ids)


def _delete_groups(session: Session, sample_ids: list[UUID]) -> None:
    """Delete group records."""
    _delete_where_column_in(session, GroupTable, GroupTable.sample_id, sample_ids)


def _delete_videos(session: Session, sample_ids: list[UUID]) -> None:
    """Delete videos."""
    _delete_where_column_in(session, VideoTable, VideoTable.sample_id, sample_ids)


def _delete_images(session: Session, sample_ids: list[UUID]) -> None:
    """Delete images."""
    _delete_where_column_in(session, ImageTable, ImageTable.sample_id, sample_ids)


def _delete_samples(session: Session, sample_ids: list[UUID]) -> None:
    """Delete samples."""
    _delete_where_column_in(session, SampleTable, SampleTable.sample_id, sample_ids)


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
    _delete_where_column_in(session, TagTable, TagTable.collection_id, collection_ids)


def _delete_embedding_models(session: Session, collection_ids: list[UUID]) -> None:
    """Delete embedding models for the given collections."""
    _delete_where_column_in(
        session, EmbeddingModelTable, EmbeddingModelTable.collection_id, collection_ids
    )


def _delete_evaluation_sample_metrics(session: Session, dataset_id: UUID) -> None:
    """Delete evaluation sample metrics for the given dataset."""
    run_ids_subquery = (
        select(EvaluationRunTable.id)
        .join(
            CollectionTable,
            col(EvaluationRunTable.gt_annotation_collection_id)
            == col(CollectionTable.collection_id),
        )
        .where(col(CollectionTable.dataset_id) == dataset_id)
    )
    session.exec(
        delete(EvaluationSampleMetricTable).where(
            col(EvaluationSampleMetricTable.evaluation_run_id).in_(run_ids_subquery)
        )
    )


def _delete_evaluation_annotation_metrics(session: Session, dataset_id: UUID) -> None:
    """Delete evaluation annotation metrics for the given dataset."""
    run_ids_subquery = (
        select(EvaluationRunTable.id)
        .join(
            CollectionTable,
            col(EvaluationRunTable.gt_annotation_collection_id)
            == col(CollectionTable.collection_id),
        )
        .where(col(CollectionTable.dataset_id) == dataset_id)
    )
    session.exec(
        delete(EvaluationAnnotationMetricTable).where(
            col(EvaluationAnnotationMetricTable.evaluation_run_id).in_(run_ids_subquery)
        )
    )


def _delete_evaluation_runs(session: Session, dataset_id: UUID) -> None:
    """Delete evaluation runs for the given dataset."""
    collection_ids_subquery = select(CollectionTable.collection_id).where(
        col(CollectionTable.dataset_id) == dataset_id
    )
    session.exec(
        delete(EvaluationRunTable).where(
            col(EvaluationRunTable.gt_annotation_collection_id).in_(collection_ids_subquery)
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
