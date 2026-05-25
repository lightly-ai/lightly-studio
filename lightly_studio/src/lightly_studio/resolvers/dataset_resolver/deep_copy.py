"""Deep copy resolver for collections."""

from __future__ import annotations

import copy
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any, TypeVar
from uuid import UUID, uuid4

from sqlmodel import Session, SQLModel, col, select

from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
    AnnotationType,
)
from lightly_studio.models.annotation.object_detection import (
    ObjectDetectionAnnotationTable,
)
from lightly_studio.models.annotation.object_track import ObjectTrackTable
from lightly_studio.models.annotation.segmentation import (
    SegmentationAnnotationTable,
)
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

T = TypeVar("T", bound=SQLModel)

# Fields to exclude when copying - these have default_factory and should be regenerated.
_EXCLUDE_ON_COPY: set[str] = {"created_at", "updated_at"}


@dataclass
class DeepCopyContext:
    """Holds ID mappings (old ID -> new ID) during deep copy operation."""

    collection_map: dict[UUID, UUID] = field(default_factory=dict)
    sample_map: dict[UUID, UUID] = field(default_factory=dict)
    tag_map: dict[UUID, UUID] = field(default_factory=dict)
    object_track_map: dict[UUID, UUID] = field(default_factory=dict)
    annotation_label_map: dict[UUID, UUID] = field(default_factory=dict)
    embedding_model_map: dict[UUID, UUID] = field(default_factory=dict)
    evaluation_run_map: dict[UUID, UUID] = field(default_factory=dict)
    new_dataset_id: UUID | None = None
    # If set, restricts which samples (and their dependents) are copied.
    # Sample-level entities that reference a sample outside this set are skipped.
    sample_id_filter: set[UUID] | None = None


def deep_copy(
    session: Session,
    dataset_id: UUID,
    copy_name: str,
) -> CollectionTable:
    """Deep copy a dataset with all related entities.

    This performs a complete deep copy of a dataset, creating new UUIDs for all
    entities while preserving relationships through ID remapping.

    Args:
        session: Database session.
        dataset_id: Dataset ID to copy.
        copy_name: Name for the new dataset.

    Returns:
        The newly created root collection.
    """
    return _deep_copy_impl(
        session=session,
        dataset_id=dataset_id,
        copy_name=copy_name,
        sample_id_filter=None,
    )


def deep_copy_subset(
    session: Session,
    dataset_id: UUID,
    copy_name: str,
    sample_ids: Iterable[UUID],
) -> CollectionTable:
    """Deep copy a dataset, restricted to the given samples.

    The full collection hierarchy and dataset-level entities (tags, labels, embedding
    models, object tracks, evaluation runs) are always copied.

    Sample-level rows are copied only for samples in ``sample_ids`` and for their
    dependents (annotations, video frames, and captions whose ``parent_sample_id`` is
    in the set). Pass parent samples (images / videos / frames) and their
    annotations/captions/frames are pulled in automatically.

    Sample IDs that do not exist in the dataset are ignored.

    Args:
        session: Database session.
        dataset_id: Dataset ID to copy from.
        copy_name: Name for the new dataset.
        sample_ids: Sample IDs from the original dataset to include in the copy.

    Returns:
        The newly created root collection.
    """
    initial = set(sample_ids)
    expanded = _expand_sample_id_filter(session=session, sample_ids=initial)
    return _deep_copy_impl(
        session=session,
        dataset_id=dataset_id,
        copy_name=copy_name,
        sample_id_filter=expanded,
    )


def _expand_sample_id_filter(session: Session, sample_ids: set[UUID]) -> set[UUID]:
    """Expand a sample-id set to include dependents that are themselves samples.

    Annotations, video frames, and captions each have their own ``SampleTable`` row
    that references a parent sample via ``parent_sample_id``. When the caller asks
    for parent samples, we transitively pull in those child sample rows so that the
    sample-level filter passes them through to the copy.
    """
    if not sample_ids:
        return sample_ids
    expanded: set[UUID] = set(sample_ids)
    ann_ids = session.exec(
        select(AnnotationBaseTable.sample_id).where(
            col(AnnotationBaseTable.parent_sample_id).in_(sample_ids)
        )
    ).all()
    expanded.update(ann_ids)
    frame_ids = session.exec(
        select(VideoFrameTable.sample_id).where(
            col(VideoFrameTable.parent_sample_id).in_(sample_ids)
        )
    ).all()
    expanded.update(frame_ids)
    # Captions added in case a frame parent was just added above.
    caption_ids = session.exec(
        select(CaptionTable.sample_id).where(
            col(CaptionTable.parent_sample_id).in_(expanded)
        )
    ).all()
    expanded.update(caption_ids)
    return expanded


def _deep_copy_impl(
    session: Session,
    dataset_id: UUID,
    copy_name: str,
    sample_id_filter: set[UUID] | None,
) -> CollectionTable:
    # If this fails, a new table was added. Update deep_copy to handle it, then update this count.
    table_coverage_utils.verify_table_coverage()
    ctx = DeepCopyContext(sample_id_filter=sample_id_filter)

    # 1. Create new dataset entry.
    new_dataset_id = uuid4()
    ctx.new_dataset_id = new_dataset_id
    # TODO(lukas, 03/2026): `copy_name` should be stored in DatasetTable
    db_dataset = DatasetTable(
        dataset_id=new_dataset_id,
    )
    session.add(db_dataset)
    session.flush([db_dataset])

    # 2. Copy collection hierarchy.
    hierarchy = dataset_resolver.get_hierarchy(session=session, dataset_id=dataset_id)
    root = _copy_collections(
        session=session,
        hierarchy=hierarchy,
        copy_name=copy_name,
        ctx=ctx,
        dataset_id=new_dataset_id,
    )

    # 3. Copy collection-scoped entities.
    old_collection_ids = list(ctx.collection_map.keys())
    _copy_tags(session=session, old_collection_ids=old_collection_ids, ctx=ctx)
    _copy_object_tracks(
        session=session,
        old_dataset_id=dataset_id,
        ctx=ctx,
    )
    _copy_annotation_labels(
        session=session,
        old_dataset_id=dataset_id,
        ctx=ctx,
    )
    _copy_embedding_models(session=session, old_collection_ids=old_collection_ids, ctx=ctx)
    _copy_evaluation_runs(session=session, old_dataset_id=dataset_id, ctx=ctx)
    _copy_samples(session=session, old_collection_ids=old_collection_ids, ctx=ctx)
    session.flush()

    # 4. Copy type-specific sample tables.
    old_sample_ids = list(ctx.sample_map.keys())
    _copy_images(session=session, old_sample_ids=old_sample_ids, ctx=ctx)
    _copy_videos(session=session, old_sample_ids=old_sample_ids, ctx=ctx)
    _copy_video_frames(session=session, old_sample_ids=old_sample_ids, ctx=ctx)
    _copy_groups(session=session, old_sample_ids=old_sample_ids, ctx=ctx)
    _copy_captions(session=session, old_sample_ids=old_sample_ids, ctx=ctx)
    _copy_annotations(session=session, old_sample_ids=old_sample_ids, ctx=ctx)
    session.flush()

    # 5. Copy sample attachments.
    _copy_metadata(session=session, old_sample_ids=old_sample_ids, ctx=ctx)
    _copy_embeddings(session=session, old_sample_ids=old_sample_ids, ctx=ctx)
    _copy_evaluation_sample_metrics(session=session, ctx=ctx)
    _copy_evaluation_annotation_metrics(session=session, ctx=ctx)
    session.flush()

    # 6. Copy link tables.
    _copy_sample_tag_links(session=session, old_sample_ids=old_sample_ids, ctx=ctx)
    _copy_sample_group_links(session=session, old_sample_ids=old_sample_ids, ctx=ctx)
    _copy_annotation_collection_coverage(session=session, ctx=ctx)

    session.commit()

    return root


def _copy_collections(
    session: Session,
    hierarchy: list[CollectionTable],
    copy_name: str,
    ctx: DeepCopyContext,
    dataset_id: UUID,
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
                "dataset_id": dataset_id,
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
    stmt = select(SampleTable).where(col(SampleTable.collection_id).in_(old_collection_ids))
    if ctx.sample_id_filter is not None:
        stmt = stmt.where(col(SampleTable.sample_id).in_(ctx.sample_id_filter))
    samples = session.exec(stmt).all()

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
    old_dataset_id: UUID,
    ctx: DeepCopyContext,
) -> None:
    """Copy annotation labels belonging to a dataset."""
    labels = session.exec(
        select(AnnotationLabelTable).where(AnnotationLabelTable.dataset_id == old_dataset_id)
    ).all()

    for old_label in labels:
        new_id = uuid4()
        ctx.annotation_label_map[old_label.annotation_label_id] = new_id

        new_label = _copy_with_updates(
            old_label,
            {"annotation_label_id": new_id, "dataset_id": ctx.new_dataset_id},
        )
        session.add(new_label)


def _copy_embedding_models(
    session: Session,
    old_collection_ids: list[UUID],
    ctx: DeepCopyContext,
) -> None:
    """Copy embedding models, remapping collection_id."""
    models = session.exec(
        select(EmbeddingModelTable).where(
            col(EmbeddingModelTable.collection_id).in_(old_collection_ids)
        )
    ).all()

    for old_model in models:
        new_id = uuid4()
        ctx.embedding_model_map[old_model.embedding_model_id] = new_id

        new_model = _copy_with_updates(
            old_model,
            {
                "embedding_model_id": new_id,
                "collection_id": ctx.collection_map[old_model.collection_id],
            },
        )
        session.add(new_model)


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
        # Skip frames whose parent video is not in the copied subset.
        if old_frame.parent_sample_id not in ctx.sample_map:
            continue
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
        # Skip captions whose parent sample is not in the copied subset.
        if old_caption.parent_sample_id not in ctx.sample_map:
            continue
        new_caption = _copy_with_updates(
            old_caption,
            {
                "sample_id": ctx.sample_map[old_caption.sample_id],
                "parent_sample_id": ctx.sample_map[old_caption.parent_sample_id],
            },
        )
        session.add(new_caption)


def _copy_object_tracks(
    session: Session,
    old_dataset_id: UUID,
    ctx: DeepCopyContext,
) -> None:
    """Copy object tracks, remapping dataset ID."""
    tracks = session.exec(
        select(ObjectTrackTable).where(col(ObjectTrackTable.dataset_id) == old_dataset_id)
    ).all()

    for old_track in tracks:
        new_track_id = uuid4()
        ctx.object_track_map[old_track.object_track_id] = new_track_id
        new_track = _copy_with_updates(
            old_track,
            {
                "object_track_id": new_track_id,
                "object_track_number": old_track.object_track_number,
                "dataset_id": ctx.new_dataset_id,
            },
        )
        session.add(new_track)


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
        # Skip annotations whose parent sample is not in the copied subset.
        if old_ann.parent_sample_id not in ctx.sample_map:
            continue
        new_sample_id = ctx.sample_map[old_ann.sample_id]
        new_object_track_id = (
            ctx.object_track_map[old_ann.object_track_id]
            if old_ann.object_track_id is not None
            else None
        )

        new_ann = _copy_with_updates(
            old_ann,
            {
                "sample_id": new_sample_id,
                "annotation_label_id": ctx.annotation_label_map[old_ann.annotation_label_id],
                "parent_sample_id": ctx.sample_map[old_ann.parent_sample_id],
                "object_track_id": new_object_track_id,
            },
        )
        session.add(new_ann)

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
    elif annotation_type == AnnotationType.SEGMENTATION_MASK:
        old_seg = session.get(SegmentationAnnotationTable, old_sample_id)
        if old_seg:
            new_seg = _copy_with_updates(
                old_seg,
                {"sample_id": new_sample_id},
            )
            session.add(new_seg)
    elif annotation_type == AnnotationType.CLASSIFICATION:
        # No details table for classification annotations, nothing to copy.
        pass
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
    """Copy sample embeddings, remapping sample_id and embedding_model_id."""
    embeddings = session.exec(
        select(SampleEmbeddingTable).where(col(SampleEmbeddingTable.sample_id).in_(old_sample_ids))
    ).all()

    for old_emb in embeddings:
        assert old_emb.embedding_model_id in ctx.embedding_model_map, (
            f"Embedding references model {old_emb.embedding_model_id} not in copied dataset"
        )
        new_emb = _copy_with_updates(
            old_emb,
            {
                "sample_id": ctx.sample_map[old_emb.sample_id],
                "embedding_model_id": ctx.embedding_model_map[old_emb.embedding_model_id],
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


def _copy_evaluation_runs(
    session: Session,
    old_dataset_id: UUID,
    ctx: DeepCopyContext,
) -> None:
    """Copy evaluation runs, remapping both collection FKs."""
    runs = session.exec(
        select(EvaluationRunTable)
        .join(
            CollectionTable,
            col(EvaluationRunTable.gt_annotation_collection_id)
            == col(CollectionTable.collection_id),
        )
        .where(col(CollectionTable.dataset_id) == old_dataset_id)
    ).all()

    for old_run in runs:
        new_run_id = uuid4()
        ctx.evaluation_run_map[old_run.id] = new_run_id
        new_run = _copy_with_updates(
            old_run,
            {
                "id": new_run_id,
                "gt_annotation_collection_id": ctx.collection_map[
                    old_run.gt_annotation_collection_id
                ],
                "pred_annotation_collection_id": ctx.collection_map[
                    old_run.pred_annotation_collection_id
                ],
            },
        )
        session.add(new_run)


def _copy_evaluation_sample_metrics(
    session: Session,
    ctx: DeepCopyContext,
) -> None:
    """Copy evaluation sample metrics, remapping evaluation_run_id and sample_id."""
    if not ctx.evaluation_run_map:
        return
    old_run_ids = list(ctx.evaluation_run_map.keys())
    metrics = session.exec(
        select(EvaluationSampleMetricTable).where(
            col(EvaluationSampleMetricTable.evaluation_run_id).in_(old_run_ids)
        )
    ).all()

    for old_metric in metrics:
        # Skip metrics for samples that were filtered out of the subset copy.
        if old_metric.sample_id not in ctx.sample_map:
            continue
        new_metric = _copy_with_updates(
            old_metric,
            {
                "evaluation_run_id": ctx.evaluation_run_map[old_metric.evaluation_run_id],
                "sample_id": ctx.sample_map[old_metric.sample_id],
            },
        )
        session.add(new_metric)


def _copy_evaluation_annotation_metrics(
    session: Session,
    ctx: DeepCopyContext,
) -> None:
    """Copy evaluation annotation metrics, remapping run, sample, and annotation IDs."""
    if not ctx.evaluation_run_map:
        return
    old_run_ids = list(ctx.evaluation_run_map.keys())
    metrics = session.exec(
        select(EvaluationAnnotationMetricTable).where(
            col(EvaluationAnnotationMetricTable.evaluation_run_id).in_(old_run_ids)
        )
    ).all()

    for old_metric in metrics:
        # Skip metrics for samples that were filtered out of the subset copy.
        if old_metric.sample_id not in ctx.sample_map:
            continue
        # If either annotation reference points to an excluded sample, null it
        # rather than dropping the whole metric.
        new_pred_id = (
            ctx.sample_map.get(old_metric.pred_annotation_id)
            if old_metric.pred_annotation_id is not None
            else None
        )
        new_gt_id = (
            ctx.sample_map.get(old_metric.gt_annotation_id)
            if old_metric.gt_annotation_id is not None
            else None
        )
        new_metric = _copy_with_updates(
            old_metric,
            {
                "id": uuid4(),
                "evaluation_run_id": ctx.evaluation_run_map[old_metric.evaluation_run_id],
                "sample_id": ctx.sample_map[old_metric.sample_id],
                "pred_annotation_id": new_pred_id,
                "gt_annotation_id": new_gt_id,
            },
        )
        session.add(new_metric)


def _copy_annotation_collection_coverage(
    session: Session,
    ctx: DeepCopyContext,
) -> None:
    """Copy annotation collection coverage rows, remapping collection and sample IDs."""
    if not ctx.collection_map:
        return
    old_collection_ids = list(ctx.collection_map.keys())
    rows = session.exec(
        select(AnnotationCollectionCoverageTable).where(
            col(AnnotationCollectionCoverageTable.annotation_collection_id).in_(old_collection_ids)
        )
    ).all()

    for old_row in rows:
        # Skip coverage rows whose parent sample is not in the copied subset.
        if old_row.parent_sample_id not in ctx.sample_map:
            continue
        new_row = AnnotationCollectionCoverageTable(
            annotation_collection_id=ctx.collection_map[old_row.annotation_collection_id],
            parent_sample_id=ctx.sample_map[old_row.parent_sample_id],
        )
        session.add(new_row)


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
