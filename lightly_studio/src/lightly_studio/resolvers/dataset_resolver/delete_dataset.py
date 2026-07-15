"""Delete dataset resolver for collections.

This is an enterprise-only / PostgreSQL-only operation. It deletes everything belonging to a
dataset with server-side, set-based ``DELETE``s scoped by subquery, so no rows cross the Python
boundary. All deletes run in a single transaction with one final commit.

The per-table scoping below is the source of truth for what gets deleted. If a new table with a
dataset/sample/collection FK is added, add a delete here; ``verify_table_coverage()`` fails fast
until you do.
"""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, delete, select
from sqlmodel.sql.expression import SelectOfScalar

from lightly_studio.database import db_manager
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
from lightly_studio.models.temporal_span import TemporalSpanTable
from lightly_studio.models.video import VideoFrameTable, VideoTable
from lightly_studio.resolvers import dataset_resolver
from lightly_studio.resolvers.dataset_resolver import table_coverage_utils

# Execution options for every bulk DELETE below. An ORM-enabled DELETE with a subquery predicate
# defaults to ``synchronize_session="fetch"``: SQLAlchemy first SELECTs every matching primary key
# into Python to evict it from the session's identity map, so peak memory scales with the number
# of deleted rows. Nothing is loaded in this session, so we disable synchronization and the delete
# runs entirely server-side with bounded memory regardless of dataset size.
_DELETE_EXECUTION_OPTIONS = {"synchronize_session": False}


def delete_dataset(
    session: Session,
    dataset_id: UUID,
) -> None:
    """Delete a dataset with all related entities.

    This performs a complete delete of a dataset, removing all associated samples, tags,
    annotations, embeddings, metadata, etc. It is enterprise-only and runs on PostgreSQL only.

    Args:
        session: Database session (must be bound to PostgreSQL).
        dataset_id: Dataset ID to delete.

    Raises:
        NotImplementedError: If the session is not bound to PostgreSQL.
        ValueError: If the dataset does not exist.
    """
    db_manager.require_postgres_backend(session)
    # Fails if new tables were added without updating this function.
    table_coverage_utils.verify_table_coverage()
    # Validate existence (raises ValueError if the dataset is not found).
    dataset_resolver.get_root_collection(session=session, dataset_id=dataset_id)

    # Delete child -> parent in a single transaction. PostgreSQL checks immediate FKs at statement
    # end, so no interphase commits are needed.

    # 1. Tables that reference annotation_base.
    _delete_object_detection_annotations(session=session, dataset_id=dataset_id)
    _delete_segmentation_annotations(session=session, dataset_id=dataset_id)
    _delete_temporal_spans(session=session, dataset_id=dataset_id)
    _delete_evaluation_sample_metrics(session=session, dataset_id=dataset_id)
    _delete_evaluation_annotation_metrics(session=session, dataset_id=dataset_id)

    # 2. annotation_base and the sample link tables.
    _delete_annotation_base(session=session, dataset_id=dataset_id)
    _delete_sample_tag_links(session=session, dataset_id=dataset_id)
    # Must precede groups (SampleGroupLinkTable.parent_sample_id -> GroupTable).
    _delete_sample_group_links(session=session, dataset_id=dataset_id)

    # 3. Sample attachments.
    _delete_sample_embeddings(session=session, dataset_id=dataset_id)
    _delete_sample_metadata(session=session, dataset_id=dataset_id)
    _delete_captions(session=session, dataset_id=dataset_id)
    # Must precede videos (VideoFrameTable.parent_sample_id -> VideoTable).
    _delete_video_frames(session=session, dataset_id=dataset_id)
    _delete_annotation_collection_coverage(session=session, dataset_id=dataset_id)

    # 4. Sample type tables.
    _delete_groups(session=session, dataset_id=dataset_id)
    _delete_videos(session=session, dataset_id=dataset_id)
    _delete_images(session=session, dataset_id=dataset_id)

    # 5. Samples and collection/dataset-scoped entities.
    _delete_samples(session=session, dataset_id=dataset_id)
    _delete_annotation_labels(session=session, dataset_id=dataset_id)
    _delete_tags(session=session, dataset_id=dataset_id)
    _delete_embedding_models(session=session, dataset_id=dataset_id)
    _delete_object_tracks(session=session, dataset_id=dataset_id)
    _delete_evaluation_runs(session=session, dataset_id=dataset_id)

    # 6. Collections (single statement; self-FK satisfied at statement end).
    _delete_collections(session=session, dataset_id=dataset_id)

    # 7. The dataset row itself.
    _delete_dataset(session=session, dataset_id=dataset_id)

    session.commit()


def _collection_ids_subquery(dataset_id: UUID) -> SelectOfScalar[UUID]:
    """Subquery selecting all collection IDs belonging to the dataset."""
    return select(CollectionTable.collection_id).where(
        col(CollectionTable.dataset_id) == dataset_id
    )


def _sample_ids_subquery(dataset_id: UUID) -> SelectOfScalar[UUID]:
    """Subquery selecting all sample IDs in the dataset's collections."""
    return select(SampleTable.sample_id).where(
        col(SampleTable.collection_id).in_(_collection_ids_subquery(dataset_id))
    )


def _delete_sample_tag_links(session: Session, dataset_id: UUID) -> None:
    """Delete sample-tag links for the dataset's samples."""
    session.exec(
        delete(SampleTagLinkTable).where(
            col(SampleTagLinkTable.sample_id).in_(_sample_ids_subquery(dataset_id))
        ),
        execution_options=_DELETE_EXECUTION_OPTIONS,
    )


def _delete_sample_group_links(session: Session, dataset_id: UUID) -> None:
    """Delete sample-group links for the dataset's samples."""
    session.exec(
        delete(SampleGroupLinkTable).where(
            col(SampleGroupLinkTable.sample_id).in_(_sample_ids_subquery(dataset_id))
        ),
        execution_options=_DELETE_EXECUTION_OPTIONS,
    )


def _delete_sample_embeddings(session: Session, dataset_id: UUID) -> None:
    """Delete sample embeddings for the dataset's samples."""
    session.exec(
        delete(SampleEmbeddingTable).where(
            col(SampleEmbeddingTable.sample_id).in_(_sample_ids_subquery(dataset_id))
        ),
        execution_options=_DELETE_EXECUTION_OPTIONS,
    )


def _delete_sample_metadata(session: Session, dataset_id: UUID) -> None:
    """Delete sample metadata for the dataset's samples."""
    session.exec(
        delete(SampleMetadataTable).where(
            col(SampleMetadataTable.sample_id).in_(_sample_ids_subquery(dataset_id))
        ),
        execution_options=_DELETE_EXECUTION_OPTIONS,
    )


def _delete_object_detection_annotations(session: Session, dataset_id: UUID) -> None:
    """Delete object detection annotation details for the dataset's samples."""
    session.exec(
        delete(ObjectDetectionAnnotationTable).where(
            col(ObjectDetectionAnnotationTable.sample_id).in_(_sample_ids_subquery(dataset_id))
        ),
        execution_options=_DELETE_EXECUTION_OPTIONS,
    )


def _delete_segmentation_annotations(session: Session, dataset_id: UUID) -> None:
    """Delete segmentation annotation details for the dataset's samples."""
    session.exec(
        delete(SegmentationAnnotationTable).where(
            col(SegmentationAnnotationTable.sample_id).in_(_sample_ids_subquery(dataset_id))
        ),
        execution_options=_DELETE_EXECUTION_OPTIONS,
    )


def _delete_temporal_spans(session: Session, dataset_id: UUID) -> None:
    """Delete temporal spans for the dataset's samples."""
    session.exec(
        delete(TemporalSpanTable).where(
            col(TemporalSpanTable.sample_id).in_(_sample_ids_subquery(dataset_id))
        ),
        execution_options=_DELETE_EXECUTION_OPTIONS,
    )


def _delete_annotation_base(session: Session, dataset_id: UUID) -> None:
    """Delete annotation base records for the dataset's samples."""
    session.exec(
        delete(AnnotationBaseTable).where(
            col(AnnotationBaseTable.sample_id).in_(_sample_ids_subquery(dataset_id))
        ),
        execution_options=_DELETE_EXECUTION_OPTIONS,
    )


def _delete_annotation_collection_coverage(session: Session, dataset_id: UUID) -> None:
    """Delete annotation collection coverage rows scoped to the dataset's collections."""
    session.exec(
        delete(AnnotationCollectionCoverageTable).where(
            col(AnnotationCollectionCoverageTable.annotation_collection_id).in_(
                _collection_ids_subquery(dataset_id)
            )
        ),
        execution_options=_DELETE_EXECUTION_OPTIONS,
    )


def _delete_object_tracks(session: Session, dataset_id: UUID) -> None:
    """Delete object tracks for the given dataset."""
    session.exec(
        delete(ObjectTrackTable).where(col(ObjectTrackTable.dataset_id) == dataset_id),
        execution_options=_DELETE_EXECUTION_OPTIONS,
    )


def _delete_captions(session: Session, dataset_id: UUID) -> None:
    """Delete captions for the dataset's samples."""
    session.exec(
        delete(CaptionTable).where(
            col(CaptionTable.sample_id).in_(_sample_ids_subquery(dataset_id))
        ),
        execution_options=_DELETE_EXECUTION_OPTIONS,
    )


def _delete_video_frames(session: Session, dataset_id: UUID) -> None:
    """Delete video frames for the dataset's samples."""
    session.exec(
        delete(VideoFrameTable).where(
            col(VideoFrameTable.sample_id).in_(_sample_ids_subquery(dataset_id))
        ),
        execution_options=_DELETE_EXECUTION_OPTIONS,
    )


def _delete_groups(session: Session, dataset_id: UUID) -> None:
    """Delete group records for the dataset's samples."""
    session.exec(
        delete(GroupTable).where(col(GroupTable.sample_id).in_(_sample_ids_subquery(dataset_id))),
        execution_options=_DELETE_EXECUTION_OPTIONS,
    )


def _delete_videos(session: Session, dataset_id: UUID) -> None:
    """Delete videos for the dataset's samples."""
    session.exec(
        delete(VideoTable).where(col(VideoTable.sample_id).in_(_sample_ids_subquery(dataset_id))),
        execution_options=_DELETE_EXECUTION_OPTIONS,
    )


def _delete_images(session: Session, dataset_id: UUID) -> None:
    """Delete images for the dataset's samples."""
    session.exec(
        delete(ImageTable).where(col(ImageTable.sample_id).in_(_sample_ids_subquery(dataset_id))),
        execution_options=_DELETE_EXECUTION_OPTIONS,
    )


def _delete_samples(session: Session, dataset_id: UUID) -> None:
    """Delete samples belonging to the dataset's collections."""
    session.exec(
        delete(SampleTable).where(col(SampleTable.sample_id).in_(_sample_ids_subquery(dataset_id))),
        execution_options=_DELETE_EXECUTION_OPTIONS,
    )


def _delete_annotation_labels(session: Session, dataset_id: UUID) -> None:
    """Delete annotation labels for the dataset."""
    session.exec(
        delete(AnnotationLabelTable).where(col(AnnotationLabelTable.dataset_id) == dataset_id),
        execution_options=_DELETE_EXECUTION_OPTIONS,
    )


def _delete_tags(session: Session, dataset_id: UUID) -> None:
    """Delete tags for the dataset's collections."""
    session.exec(
        delete(TagTable).where(
            col(TagTable.collection_id).in_(_collection_ids_subquery(dataset_id))
        ),
        execution_options=_DELETE_EXECUTION_OPTIONS,
    )


def _delete_embedding_models(session: Session, dataset_id: UUID) -> None:
    """Delete embedding models for the dataset's collections."""
    session.exec(
        delete(EmbeddingModelTable).where(
            col(EmbeddingModelTable.collection_id).in_(_collection_ids_subquery(dataset_id))
        ),
        execution_options=_DELETE_EXECUTION_OPTIONS,
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
        ),
        execution_options=_DELETE_EXECUTION_OPTIONS,
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
        ),
        execution_options=_DELETE_EXECUTION_OPTIONS,
    )


def _delete_evaluation_runs(session: Session, dataset_id: UUID) -> None:
    """Delete evaluation runs for the given dataset."""
    session.exec(
        delete(EvaluationRunTable).where(
            col(EvaluationRunTable.gt_annotation_collection_id).in_(
                _collection_ids_subquery(dataset_id)
            )
        ),
        execution_options=_DELETE_EXECUTION_OPTIONS,
    )


def _delete_collections(session: Session, dataset_id: UUID) -> None:
    """Delete all collections of the dataset in a single statement.

    Deleting every collection at once satisfies the self-referential
    ``parent_collection_id`` FK: all rows are gone when the check fires at statement end.
    """
    session.exec(
        delete(CollectionTable).where(col(CollectionTable.dataset_id) == dataset_id),
        execution_options=_DELETE_EXECUTION_OPTIONS,
    )


def _delete_dataset(session: Session, dataset_id: UUID) -> None:
    """Delete the dataset record from DatasetTable."""
    session.exec(
        delete(DatasetTable).where(col(DatasetTable.dataset_id) == dataset_id),
        execution_options=_DELETE_EXECUTION_OPTIONS,
    )
