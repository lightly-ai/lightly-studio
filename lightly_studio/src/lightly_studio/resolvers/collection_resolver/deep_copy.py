"""Deep copy resolver for collections."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlmodel import Session, col, select

from lightly_studio import AnnotationType
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.annotation.instance_segmentation import (
    InstanceSegmentationAnnotationTable,
)
from lightly_studio.models.annotation.links import AnnotationTagLinkTable
from lightly_studio.models.annotation.object_detection import (
    ObjectDetectionAnnotationTable,
)
from lightly_studio.models.annotation.semantic_segmentation import (
    SemanticSegmentationAnnotationTable,
)
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.caption import CaptionTable
from lightly_studio.models.collection import CollectionTable
from lightly_studio.models.group import GroupTable, SampleGroupLinkTable
from lightly_studio.models.image import ImageTable
from lightly_studio.models.metadata import SampleMetadataTable
from lightly_studio.models.sample import SampleTable, SampleTagLinkTable
from lightly_studio.models.sample_embedding import SampleEmbeddingTable
from lightly_studio.models.tag import TagTable
from lightly_studio.models.video import VideoFrameTable, VideoTable
from lightly_studio.resolvers.collection_resolver import get_hierarchy


@dataclass
class DeepCopyContext:
    """Holds ID mappings during deep copy operation."""

    collection_map: dict[UUID, UUID] = field(default_factory=dict)
    sample_map: dict[UUID, UUID] = field(default_factory=dict)
    tag_map: dict[UUID, UUID] = field(default_factory=dict)
    annotation_label_map: dict[UUID, UUID] = field(default_factory=dict)


def deep_copy(
    session: Session,
    root_collection_id: UUID,
    new_name: str,
) -> CollectionTable:
    """Deep copy a root collection with all related entities.

    This performs a complete deep copy of a root collection, creating new UUIDs for all
    entities while preserving relationships through ID remapping.

    Args:
        session: Database session.
        root_collection_id: Root collection ID to copy.
        new_name: Name for the new collection.

    Returns:
        The newly created root collection.
    """
    ctx = DeepCopyContext()

    # 1. Copy collection hierarchy.
    hierarchy = get_hierarchy(session, root_collection_id)
    root = _copy_collections(session, hierarchy, new_name, ctx)

    # 2. Copy collection-scoped entities.
    old_collection_ids = list(ctx.collection_map.keys())
    _copy_tags(session, old_collection_ids, ctx)
    _copy_annotation_labels(session, root_collection_id, ctx)
    _copy_samples(session, old_collection_ids, ctx)
    session.flush()

    # 3. Copy type-specific sample tables.
    old_sample_ids = list(ctx.sample_map.keys())
    _copy_images(session, old_sample_ids, ctx)
    _copy_videos(session, old_sample_ids, ctx)
    _copy_video_frames(session, old_sample_ids, ctx)
    _copy_groups(session, old_sample_ids, ctx)
    _copy_captions(session, old_sample_ids, ctx)
    _copy_annotations(session, old_sample_ids, ctx)
    session.flush()

    # 4. Copy sample attachments.
    _copy_metadata(session, old_sample_ids, ctx)
    _copy_embeddings(session, old_sample_ids, ctx)
    session.flush()

    # 5. Copy link tables.
    _copy_sample_tag_links(session, old_sample_ids, ctx)
    _copy_annotation_tag_links(session, old_sample_ids, ctx)
    _copy_sample_group_links(session, old_sample_ids, ctx)

    return root


def _copy_collections(
    session: Session,
    hierarchy: list[CollectionTable],
    new_name: str,
    ctx: DeepCopyContext,
) -> CollectionTable:
    """Copy collection hierarchy, maintaining parent-child relationships."""
    root: CollectionTable | None = None
    old_root_name = hierarchy[0].name

    # Generate new UUIDs for all collections and build the mapping.
    for old_coll in hierarchy:
        new_id = uuid4()
        ctx.collection_map[old_coll.collection_id] = new_id

    # Insert the copied collections one by one.
    for old_coll in hierarchy:
        new_id = ctx.collection_map[old_coll.collection_id]

        # Derive new name by replacing root prefix.
        if old_coll.name == old_root_name:
            derived_name = new_name
        else:
            derived_name = old_coll.name.replace(old_root_name, new_name, 1)

        # Remap parent_collection_id if it exists.
        new_parent_id = None
        if old_coll.parent_collection_id is not None:
            new_parent_id = ctx.collection_map[old_coll.parent_collection_id]

        new_coll = CollectionTable(
            collection_id=new_id,
            name=derived_name,
            sample_type=old_coll.sample_type,
            parent_collection_id=new_parent_id,
            group_component_name=old_coll.group_component_name,
            group_component_index=old_coll.group_component_index,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        session.add(new_coll)
        session.flush()  # Flush each collection so it's visible for FK checks.

        if root is None:
            root = new_coll

    return root  # type: ignore[return-value]


def _copy_samples(
    session: Session,
    old_collection_ids: list[UUID],
    ctx: DeepCopyContext,
) -> None:
    """Copy all samples, remapping collection_id to new collections."""
    samples = session.exec(
        select(SampleTable).where(col(SampleTable.collection_id).in_(old_collection_ids))
    ).all()

    for old_sample in samples:
        new_id = uuid4()
        ctx.sample_map[old_sample.sample_id] = new_id

        new_sample = SampleTable(
            sample_id=new_id,
            collection_id=ctx.collection_map[old_sample.collection_id],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        session.add(new_sample)


def _copy_tags(
    session: Session,
    old_collection_ids: list[UUID],
    ctx: DeepCopyContext,
) -> None:
    """Copy tags, remapping collection_id."""
    tags = session.exec(
        select(TagTable).where(col(TagTable.collection_id).in_(old_collection_ids))
    ).all()

    for old_tag in tags:
        new_id = uuid4()
        ctx.tag_map[old_tag.tag_id] = new_id

        new_tag = TagTable(
            tag_id=new_id,
            name=old_tag.name,
            description=old_tag.description,
            kind=old_tag.kind,
            collection_id=ctx.collection_map[old_tag.collection_id],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        session.add(new_tag)


def _copy_annotation_labels(
    session: Session,
    root_collection_id: UUID,
    ctx: DeepCopyContext,
) -> None:
    """Copy annotation labels (belong to root dataset only)."""
    labels = session.exec(
        select(AnnotationLabelTable).where(AnnotationLabelTable.dataset_id == root_collection_id)
    ).all()

    new_dataset_id = ctx.collection_map[root_collection_id]

    for old_label in labels:
        new_id = uuid4()
        ctx.annotation_label_map[old_label.annotation_label_id] = new_id

        new_label = AnnotationLabelTable(
            annotation_label_id=new_id,
            dataset_id=new_dataset_id,
            annotation_label_name=old_label.annotation_label_name,
            created_at=str(datetime.now(timezone.utc)),
        )
        session.add(new_label)


def _copy_videos(
    session: Session,
    old_sample_ids: list[UUID],
    ctx: DeepCopyContext,
) -> None:
    """Copy video records, remapping sample_id."""
    videos = session.exec(
        select(VideoTable).where(col(VideoTable.sample_id).in_(old_sample_ids))
    ).all()

    for old_video in videos:
        new_video = VideoTable(
            sample_id=ctx.sample_map[old_video.sample_id],
            file_name=old_video.file_name,
            width=old_video.width,
            height=old_video.height,
            duration_s=old_video.duration_s,
            fps=old_video.fps,
            file_path_abs=old_video.file_path_abs,
        )
        session.add(new_video)


def _copy_video_frames(
    session: Session,
    old_sample_ids: list[UUID],
    ctx: DeepCopyContext,
) -> None:
    """Copy video frames, remapping both sample_id and parent_sample_id."""
    frames = session.exec(
        select(VideoFrameTable).where(col(VideoFrameTable.sample_id).in_(old_sample_ids))
    ).all()

    for old_frame in frames:
        new_frame = VideoFrameTable(
            sample_id=ctx.sample_map[old_frame.sample_id],
            frame_number=old_frame.frame_number,
            frame_timestamp_pts=old_frame.frame_timestamp_pts,
            frame_timestamp_s=old_frame.frame_timestamp_s,
            parent_sample_id=ctx.sample_map[old_frame.parent_sample_id],
            rotation_deg=old_frame.rotation_deg,
        )
        session.add(new_frame)


def _copy_images(
    session: Session,
    old_sample_ids: list[UUID],
    ctx: DeepCopyContext,
) -> None:
    """Copy image records, remapping sample_id."""
    images = session.exec(
        select(ImageTable).where(col(ImageTable.sample_id).in_(old_sample_ids))
    ).all()

    for old_image in images:
        new_image = ImageTable(
            sample_id=ctx.sample_map[old_image.sample_id],
            file_name=old_image.file_name,
            width=old_image.width,
            height=old_image.height,
            file_path_abs=old_image.file_path_abs,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        session.add(new_image)


def _copy_groups(
    session: Session,
    old_sample_ids: list[UUID],
    ctx: DeepCopyContext,
) -> None:
    """Copy group records."""
    groups = session.exec(
        select(GroupTable).where(col(GroupTable.sample_id).in_(old_sample_ids))
    ).all()

    for old_group in groups:
        new_group = GroupTable(
            sample_id=ctx.sample_map[old_group.sample_id],
        )
        session.add(new_group)


def _copy_captions(
    session: Session,
    old_sample_ids: list[UUID],
    ctx: DeepCopyContext,
) -> None:
    """Copy captions, remapping sample_id and parent_sample_id."""
    captions = session.exec(
        select(CaptionTable).where(col(CaptionTable.sample_id).in_(old_sample_ids))
    ).all()

    for old_caption in captions:
        new_caption = CaptionTable(
            sample_id=ctx.sample_map[old_caption.sample_id],
            parent_sample_id=ctx.sample_map[old_caption.parent_sample_id],
            text=old_caption.text,
            created_at=datetime.now(timezone.utc),
        )
        session.add(new_caption)


def _copy_annotations(
    session: Session,
    old_sample_ids: list[UUID],
    ctx: DeepCopyContext,
) -> None:
    """Copy annotations with their detail tables."""
    annotations = session.exec(
        select(AnnotationBaseTable).where(col(AnnotationBaseTable.sample_id).in_(old_sample_ids))
    ).all()

    for old_ann in annotations:
        new_sample_id = ctx.sample_map[old_ann.sample_id]

        new_ann = AnnotationBaseTable(
            sample_id=new_sample_id,
            annotation_type=old_ann.annotation_type,
            annotation_label_id=ctx.annotation_label_map[old_ann.annotation_label_id],
            confidence=old_ann.confidence,
            parent_sample_id=ctx.sample_map[old_ann.parent_sample_id],
            created_at=datetime.now(timezone.utc),
        )
        session.add(new_ann)

        # Copy annotation-type-specific details.
        _copy_annotation_details(session, old_ann.sample_id, new_sample_id, old_ann.annotation_type)


def _copy_annotation_details(
    session: Session,
    old_sample_id: UUID,
    new_sample_id: UUID,
    annotation_type: AnnotationType,
) -> None:
    """Copy annotation detail table based on type."""
    if annotation_type.value == "object_detection":
        old_obj_det = session.get(ObjectDetectionAnnotationTable, old_sample_id)
        if old_obj_det:
            session.add(
                ObjectDetectionAnnotationTable(
                    sample_id=new_sample_id,
                    x=old_obj_det.x,
                    y=old_obj_det.y,
                    width=old_obj_det.width,
                    height=old_obj_det.height,
                )
            )
    elif annotation_type.value == "instance_segmentation":
        old_inst_seg = session.get(InstanceSegmentationAnnotationTable, old_sample_id)
        if old_inst_seg:
            session.add(
                InstanceSegmentationAnnotationTable(
                    sample_id=new_sample_id,
                    x=old_inst_seg.x,
                    y=old_inst_seg.y,
                    width=old_inst_seg.width,
                    height=old_inst_seg.height,
                    segmentation_mask=old_inst_seg.segmentation_mask,
                )
            )
    elif annotation_type.value == "semantic_segmentation":
        old_sem_seg = session.get(SemanticSegmentationAnnotationTable, old_sample_id)
        if old_sem_seg:
            session.add(
                SemanticSegmentationAnnotationTable(
                    sample_id=new_sample_id,
                    segmentation_mask=old_sem_seg.segmentation_mask,
                )
            )


def _copy_metadata(
    session: Session,
    old_sample_ids: list[UUID],
    ctx: DeepCopyContext,
) -> None:
    """Copy sample metadata."""
    metadata_records = session.exec(
        select(SampleMetadataTable).where(col(SampleMetadataTable.sample_id).in_(old_sample_ids))
    ).all()

    for old_meta in metadata_records:
        new_meta = SampleMetadataTable(
            custom_metadata_id=uuid4(),
            sample_id=ctx.sample_map[old_meta.sample_id],
            data=copy.deepcopy(old_meta.data),
            metadata_schema=copy.deepcopy(old_meta.metadata_schema),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        session.add(new_meta)


def _copy_embeddings(
    session: Session,
    old_sample_ids: list[UUID],
    ctx: DeepCopyContext,
) -> None:
    """Copy sample embeddings, remapping sample_id but keeping the same embedding_model_id.

    Embedding models are shared resources (representing trained ML models) and should
    not be copied. The new samples reference the same embedding models as the originals.
    """
    embeddings = session.exec(
        select(SampleEmbeddingTable).where(col(SampleEmbeddingTable.sample_id).in_(old_sample_ids))
    ).all()

    for old_emb in embeddings:
        new_emb = SampleEmbeddingTable(
            sample_id=ctx.sample_map[old_emb.sample_id],
            embedding_model_id=old_emb.embedding_model_id,
            embedding=old_emb.embedding.copy(),
        )
        session.add(new_emb)


def _copy_sample_tag_links(
    session: Session,
    old_sample_ids: list[UUID],
    ctx: DeepCopyContext,
) -> None:
    """Copy sample-tag links."""
    links = session.exec(
        select(SampleTagLinkTable).where(col(SampleTagLinkTable.sample_id).in_(old_sample_ids))
    ).all()

    for old_link in links:
        if (
            old_link.sample_id is not None
            and old_link.tag_id is not None
            and old_link.tag_id in ctx.tag_map
        ):
            new_link = SampleTagLinkTable(
                sample_id=ctx.sample_map[old_link.sample_id],
                tag_id=ctx.tag_map[old_link.tag_id],
            )
            session.add(new_link)


def _copy_annotation_tag_links(
    session: Session,
    old_sample_ids: list[UUID],
    ctx: DeepCopyContext,
) -> None:
    """Copy annotation-tag links."""
    links = session.exec(
        select(AnnotationTagLinkTable).where(
            col(AnnotationTagLinkTable.annotation_sample_id).in_(old_sample_ids)
        )
    ).all()

    for old_link in links:
        if (
            old_link.annotation_sample_id is not None
            and old_link.tag_id is not None
            and old_link.tag_id in ctx.tag_map
        ):
            new_link = AnnotationTagLinkTable(
                annotation_sample_id=ctx.sample_map[old_link.annotation_sample_id],
                tag_id=ctx.tag_map[old_link.tag_id],
            )
            session.add(new_link)


def _copy_sample_group_links(
    session: Session,
    old_sample_ids: list[UUID],
    ctx: DeepCopyContext,
) -> None:
    """Copy sample-group links."""
    links = session.exec(
        select(SampleGroupLinkTable).where(col(SampleGroupLinkTable.sample_id).in_(old_sample_ids))
    ).all()

    for old_link in links:
        if old_link.parent_sample_id in ctx.sample_map:
            new_link = SampleGroupLinkTable(
                sample_id=ctx.sample_map[old_link.sample_id],
                parent_sample_id=ctx.sample_map[old_link.parent_sample_id],
            )
            session.add(new_link)
