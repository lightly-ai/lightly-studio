"""Deep copy resolver for collections."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, TypeVar
from uuid import UUID, uuid4

from sqlmodel import Session, SQLModel, col, select

from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
    AnnotationType,
)
from lightly_studio.models.annotation.links import AnnotationTagLinkTable
from lightly_studio.models.annotation.object_detection import (
    ObjectDetectionAnnotationTable,
)
from lightly_studio.models.annotation.segmentation import (
    SegmentationAnnotationTable,
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
from lightly_studio.resolvers import collection_resolver

# Expected number of SQLModel tables to be copied.
_COPIED_TABLES_COUNT = 17
# Tables not relevant for deep copy:
# - embedding_model (shared resource, not copied)
# - setting (not relevant for collections)
# - two_dim_embeddings (will be regenerated anyway)
_NOT_COPIED_TABLES_COUNT = 3

_TOTAL_TABLES_COUNT = _COPIED_TABLES_COUNT + _NOT_COPIED_TABLES_COUNT

T = TypeVar("T", bound=SQLModel)

# Fields to exclude when copying - these have default_factory and should be regenerated.
_EXCLUDE_ON_COPY: set[str] = {"created_at", "updated_at"}


@dataclass
class DeepCopyContext:
    """Holds ID mappings (old ID -> new ID) during deep copy operation."""

    collection_map: dict[UUID, UUID] = field(default_factory=dict)
    sample_map: dict[UUID, UUID] = field(default_factory=dict)
    tag_map: dict[UUID, UUID] = field(default_factory=dict)
    annotation_label_map: dict[UUID, UUID] = field(default_factory=dict)


def deep_copy(
    session: Session,
    root_collection_id: UUID,
    copy_name: str,
) -> CollectionTable:
    """Deep copy a root collection with all related entities.

    This performs a complete deep copy of a root collection, creating new UUIDs for all
    entities while preserving relationships through ID remapping.

    Args:
        session: Database session.
        root_collection_id: Root collection ID to copy.
        copy_name: Name for the new collection.

    Returns:
        The newly created root collection.
    """
    # If this fails, a new table was added. Update deep_copy to handle it, then update this count.
    _verify_table_coverage()

    ctx = DeepCopyContext()

    # 1. Copy collection hierarchy.
    hierarchy = collection_resolver.get_hierarchy(session=session, dataset_id=root_collection_id)
    root = _copy_collections(session=session, hierarchy=hierarchy, copy_name=copy_name, ctx=ctx)

    # 2. Copy collection-scoped entities.
    old_collection_ids = list(ctx.collection_map.keys())
    _copy_tags(session=session, old_collection_ids=old_collection_ids, ctx=ctx)
    _copy_annotation_labels(session=session, root_collection_id=root_collection_id, ctx=ctx)
    _copy_samples(session=session, old_collection_ids=old_collection_ids, ctx=ctx)
    session.flush()

    # 3. Copy type-specific sample tables.
    old_sample_ids = list(ctx.sample_map.keys())
    _copy_images(session=session, old_sample_ids=old_sample_ids, ctx=ctx)
    _copy_videos(session=session, old_sample_ids=old_sample_ids, ctx=ctx)
    _copy_video_frames(session=session, old_sample_ids=old_sample_ids, ctx=ctx)
    _copy_groups(session=session, old_sample_ids=old_sample_ids, ctx=ctx)
    _copy_captions(session=session, old_sample_ids=old_sample_ids, ctx=ctx)
    _copy_annotations(session=session, old_sample_ids=old_sample_ids, ctx=ctx)
    session.flush()

    # 4. Copy sample attachments.
    _copy_metadata(session=session, old_sample_ids=old_sample_ids, ctx=ctx)
    _copy_embeddings(session=session, old_sample_ids=old_sample_ids, ctx=ctx)
    session.flush()

    # 5. Copy link tables.
    _copy_sample_tag_links(session=session, old_sample_ids=old_sample_ids, ctx=ctx)
    _copy_annotation_tag_links(session=session, old_sample_ids=old_sample_ids, ctx=ctx)
    _copy_sample_group_links(session=session, old_sample_ids=old_sample_ids, ctx=ctx)

    session.commit()

    return root


def _copy_collections(
    session: Session,
    hierarchy: list[CollectionTable],
    copy_name: str,
    ctx: DeepCopyContext,
) -> CollectionTable:
    """Copy collection hierarchy, maintaining parent-child relationships."""
    root: CollectionTable | None = None
    old_root_name = hierarchy[0].name

    # Generate new UUIDs for all collections and build the mapping.
    ctx.collection_map = {old_coll.collection_id: uuid4() for old_coll in hierarchy}

    # Insert the copied collections one by one.
    for old_coll in hierarchy:
        new_id = ctx.collection_map[old_coll.collection_id]

        # Derive new name by replacing root prefix.
        if old_coll.name == old_root_name:
            derived_name = copy_name
        else:
            derived_name = old_coll.name.replace(old_root_name, copy_name, 1)

        # Remap parent_collection_id if it exists.
        new_parent_id = None
        if old_coll.parent_collection_id is not None:
            new_parent_id = ctx.collection_map[old_coll.parent_collection_id]

        new_coll = _copy_with_updates(
            old_coll,
            {
                "collection_id": new_id,
                "name": derived_name,
                "parent_collection_id": new_parent_id,
            },
        )
        session.add(new_coll)
        session.flush()  # Flush each collection so it's visible for FK checks.

        # Keep track of the new root collection.
        # The root is the first collection in the hierarchy argument.
        if root is None:
            root = new_coll

    assert root is not None
    return root


def _copy_samples(
    session: Session,
    old_collection_ids: list[UUID],
    ctx: DeepCopyContext,
) -> None:
    """Copy all samples, remapping collection_id to new collections."""
    # TODO (Mihnea, 01/2026): Handle large collections with batching if needed.
    samples = session.exec(
        select(SampleTable).where(col(SampleTable.collection_id).in_(old_collection_ids))
    ).all()

    for old_sample in samples:
        new_id = uuid4()
        ctx.sample_map[old_sample.sample_id] = new_id

        new_sample = _copy_with_updates(
            old_sample,
            {
                "sample_id": new_id,
                "collection_id": ctx.collection_map[old_sample.collection_id],
            },
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

        new_tag = _copy_with_updates(
            old_tag,
            {
                "tag_id": new_id,
                "collection_id": ctx.collection_map[old_tag.collection_id],
            },
        )
        session.add(new_tag)


def _copy_annotation_labels(
    session: Session,
    root_collection_id: UUID,
    ctx: DeepCopyContext,
) -> None:
    """Copy annotation labels (belong to root collection only)."""
    labels = session.exec(
        select(AnnotationLabelTable).where(AnnotationLabelTable.dataset_id == root_collection_id)
    ).all()

    new_root_collection_id = ctx.collection_map[root_collection_id]

    for old_label in labels:
        new_id = uuid4()
        ctx.annotation_label_map[old_label.annotation_label_id] = new_id

        new_label = _copy_with_updates(
            old_label,
            {
                "annotation_label_id": new_id,
                "dataset_id": new_root_collection_id,
            },
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
        new_video = _copy_with_updates(
            old_video,
            {"sample_id": ctx.sample_map[old_video.sample_id]},
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
        new_frame = _copy_with_updates(
            old_frame,
            {
                "sample_id": ctx.sample_map[old_frame.sample_id],
                "parent_sample_id": ctx.sample_map[old_frame.parent_sample_id],
            },
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
        new_image = _copy_with_updates(
            old_image,
            {"sample_id": ctx.sample_map[old_image.sample_id]},
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
        new_group = _copy_with_updates(
            old_group,
            {"sample_id": ctx.sample_map[old_group.sample_id]},
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
        new_caption = _copy_with_updates(
            old_caption,
            {
                "sample_id": ctx.sample_map[old_caption.sample_id],
                "parent_sample_id": ctx.sample_map[old_caption.parent_sample_id],
            },
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

        new_ann = _copy_with_updates(
            old_ann,
            {
                "sample_id": new_sample_id,
                "annotation_label_id": ctx.annotation_label_map[old_ann.annotation_label_id],
                "parent_sample_id": ctx.sample_map[old_ann.parent_sample_id],
            },
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
    if annotation_type == AnnotationType.OBJECT_DETECTION:
        old_obj_det = session.get(ObjectDetectionAnnotationTable, old_sample_id)
        if old_obj_det:
            new_obj_det = _copy_with_updates(
                old_obj_det,
                {"sample_id": new_sample_id},
            )
            session.add(new_obj_det)
    elif annotation_type in (
        AnnotationType.INSTANCE_SEGMENTATION,
        AnnotationType.SEMANTIC_SEGMENTATION,
    ):
        old_seg = session.get(SegmentationAnnotationTable, old_sample_id)
        if old_seg:
            new_seg = _copy_with_updates(
                old_seg,
                {"sample_id": new_sample_id},
            )
            session.add(new_seg)
    else:
        raise ValueError(f"Unsupported annotation type: {annotation_type}")


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
        new_meta = _copy_with_updates(
            old_meta,
            {
                "custom_metadata_id": uuid4(),
                "sample_id": ctx.sample_map[old_meta.sample_id],
            },
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
        new_emb = _copy_with_updates(
            old_emb,
            {
                "sample_id": ctx.sample_map[old_emb.sample_id],
            },
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


def _copy_with_updates(
    entity: T,
    updates: dict[str, Any],
    deep: bool = False,
    exclude: set[str] | None = None,
) -> T:
    """Create a copy of an entity with specified field updates.

    Uses model_dump() to extract field values, then reconstructs a new instance.
    This ensures new fields added to models are automatically included in copies.

    Args:
        entity: Source entity to copy.
        updates: Fields to override (e.g., remapped IDs).
        deep: If True, apply copy.deepcopy() after model_dump(). Only needed
            for non-JSON mutable fields; JSON-typed fields are already
            deep copied by Pydantic's serialization.
        exclude: Fields to exclude from copy. Excluded fields will use model defaults.
                 Defaults to _EXCLUDE_ON_COPY (created_at, updated_at).

    Returns:
        New instance of the same type with updates applied.
    """
    if exclude is None:
        exclude = _EXCLUDE_ON_COPY
    data = entity.model_dump(exclude=exclude)
    if deep:
        data = copy.deepcopy(data)
    data.update(updates)
    return type(entity)(**data)


def _verify_table_coverage() -> None:
    """Verify that all relevant SQLModel tables are handled in deep copy.

    Raises:
        RuntimeError: If the number of SQLModel tables has changed.
    """
    actual_count = len(SQLModel.metadata.tables)
    assert actual_count == _TOTAL_TABLES_COUNT, (
        f"Table count changed ({actual_count} != {_TOTAL_TABLES_COUNT}). "
        "Update deep_copy to handle new tables, then update this count."
    )
