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
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.caption import CaptionTable
from lightly_studio.models.collection import CollectionTable
from lightly_studio.models.embedding_model import EmbeddingModelTable
from lightly_studio.models.group import GroupTable, SampleGroupLinkTable
from lightly_studio.models.image import ImageTable
from lightly_studio.models.metadata import SampleMetadataTable
from lightly_studio.models.sample import SampleTable, SampleTagLinkTable
from lightly_studio.models.sample_embedding import SampleEmbeddingTable
from lightly_studio.models.tag import TagTable
from lightly_studio.models.video import VideoFrameTable, VideoTable
from lightly_studio.resolvers import collection_resolver
from lightly_studio.resolvers.collection_resolver import (
    table_coverage_utils,
)


def delete_dataset(
    session: Session,
    root_collection_id: UUID,
) -> None:
    """Delete a root collection with all related entities.

    This performs a complete delete of a root collection, removing all associated samples, tags,
    annotations, embeddings, metadata, etc.

    Args:
        session: Database session.
        root_collection_id: Root collection ID to delete.

    Raises:
        ValueError: If the collection is not a root collection.
    """
    # Ensure all tables are handled - fails if new tables were added without updating this function.
    table_coverage_utils.verify_table_coverage()

    # Verify it's a root collection.
    root = collection_resolver.get_by_id(session=session, collection_id=root_collection_id)
    if root is None:
        raise ValueError(f"Collection with ID {root_collection_id} not found.")
    if root.parent_collection_id is not None:
        raise ValueError("Only root collections can be deleted.")

    # Get the hierarchy and collect all IDs.
    hierarchy = collection_resolver.get_hierarchy(session=session, dataset_id=root_collection_id)
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
    _delete_annotation_labels(session=session, root_collection_id=root_collection_id)
    _delete_tags(session=session, collection_ids=collection_ids)
    _delete_embedding_models(session=session, collection_ids=collection_ids)
    _delete_object_tracks(session=session, collection_ids=collection_ids)
    session.commit()  # Required before deleting collections.

    # 6. Delete collections (with individual commits due to self-referential FKs).
    _delete_collections(session=session, collection_ids=collection_ids)


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
    session.exec(  # type: ignore[call-overload]
        delete(SampleTagLinkTable).where(col(SampleTagLinkTable.sample_id).in_(sample_ids))
    )


def _delete_sample_group_links(session: Session, sample_ids: list[UUID]) -> None:
    """Delete sample-group links for the given samples."""
    if not sample_ids:
        return
    session.exec(  # type: ignore[call-overload]
        delete(SampleGroupLinkTable).where(col(SampleGroupLinkTable.sample_id).in_(sample_ids))
    )


def _delete_sample_embeddings(session: Session, sample_ids: list[UUID]) -> None:
    """Delete sample embeddings for the given samples."""
    if not sample_ids:
        return
    session.exec(  # type: ignore[call-overload]
        delete(SampleEmbeddingTable).where(col(SampleEmbeddingTable.sample_id).in_(sample_ids))
    )


def _delete_sample_metadata(session: Session, sample_ids: list[UUID]) -> None:
    """Delete sample metadata for the given samples."""
    if not sample_ids:
        return
    session.exec(  # type: ignore[call-overload]
        delete(SampleMetadataTable).where(col(SampleMetadataTable.sample_id).in_(sample_ids))
    )


def _delete_object_detection_annotations(session: Session, sample_ids: list[UUID]) -> None:
    """Delete object detection annotation details."""
    if not sample_ids:
        return
    session.exec(  # type: ignore[call-overload]
        delete(ObjectDetectionAnnotationTable).where(
            col(ObjectDetectionAnnotationTable.sample_id).in_(sample_ids)
        )
    )


def _delete_segmentation_annotations(session: Session, sample_ids: list[UUID]) -> None:
    """Delete segmentation annotation details."""
    if not sample_ids:
        return
    session.exec(  # type: ignore[call-overload]
        delete(SegmentationAnnotationTable).where(
            col(SegmentationAnnotationTable.sample_id).in_(sample_ids)
        )
    )


def _delete_annotation_base(session: Session, sample_ids: list[UUID]) -> None:
    """Delete annotation base records."""
    if not sample_ids:
        return
    session.exec(  # type: ignore[call-overload]
        delete(AnnotationBaseTable).where(col(AnnotationBaseTable.sample_id).in_(sample_ids))
    )


def _delete_object_tracks(session: Session, collection_ids: list[UUID]) -> None:
    """Delete object tracks for the given collections."""
    if not collection_ids:
        return
    session.exec(  # type: ignore[call-overload]
        delete(ObjectTrackTable).where(col(ObjectTrackTable.dataset_id).in_(collection_ids))
    )


def _delete_captions(session: Session, sample_ids: list[UUID]) -> None:
    """Delete captions."""
    if not sample_ids:
        return
    session.exec(  # type: ignore[call-overload]
        delete(CaptionTable).where(col(CaptionTable.sample_id).in_(sample_ids))
    )


def _delete_video_frames(session: Session, sample_ids: list[UUID]) -> None:
    """Delete video frames."""
    if not sample_ids:
        return
    session.exec(  # type: ignore[call-overload]
        delete(VideoFrameTable).where(col(VideoFrameTable.sample_id).in_(sample_ids))
    )


def _delete_groups(session: Session, sample_ids: list[UUID]) -> None:
    """Delete group records."""
    if not sample_ids:
        return
    session.exec(  # type: ignore[call-overload]
        delete(GroupTable).where(col(GroupTable.sample_id).in_(sample_ids))
    )


def _delete_videos(session: Session, sample_ids: list[UUID]) -> None:
    """Delete videos."""
    if not sample_ids:
        return
    session.exec(  # type: ignore[call-overload]
        delete(VideoTable).where(col(VideoTable.sample_id).in_(sample_ids))
    )


def _delete_images(session: Session, sample_ids: list[UUID]) -> None:
    """Delete images."""
    if not sample_ids:
        return
    session.exec(  # type: ignore[call-overload]
        delete(ImageTable).where(col(ImageTable.sample_id).in_(sample_ids))
    )


def _delete_samples(session: Session, sample_ids: list[UUID]) -> None:
    """Delete samples."""
    if not sample_ids:
        return
    session.exec(  # type: ignore[call-overload]
        delete(SampleTable).where(col(SampleTable.sample_id).in_(sample_ids))
    )


def _delete_annotation_labels(session: Session, root_collection_id: UUID) -> None:
    """Delete annotation labels for the root collection."""
    session.exec(  # type: ignore[call-overload]
        delete(AnnotationLabelTable).where(
            col(AnnotationLabelTable.dataset_id) == root_collection_id
        )
    )


def _delete_tags(session: Session, collection_ids: list[UUID]) -> None:
    """Delete tags for the given collections."""
    if not collection_ids:
        return
    session.exec(  # type: ignore[call-overload]
        delete(TagTable).where(col(TagTable.collection_id).in_(collection_ids))
    )


def _delete_embedding_models(session: Session, collection_ids: list[UUID]) -> None:
    """Delete embedding models for the given collections."""
    if not collection_ids:
        return
    session.exec(  # type: ignore[call-overload]
        delete(EmbeddingModelTable).where(
            col(EmbeddingModelTable.collection_id).in_(collection_ids)
        )
    )


def _delete_collections(session: Session, collection_ids: list[UUID]) -> None:
    """Delete collections in reverse order (children first)."""
    if not collection_ids:
        return
    # Reverse the list to delete children before parents
    for collection_id in reversed(collection_ids):
        session.exec(  # type: ignore[call-overload]
            delete(CollectionTable).where(col(CollectionTable.collection_id) == collection_id)
        )
        session.commit()
