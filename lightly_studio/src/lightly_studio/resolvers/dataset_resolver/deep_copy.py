"""Deep copy resolver for collections (PostgreSQL, set-based).

Copies an entire dataset (collections, samples, annotations, embeddings, metadata,
tags, groups, evaluation data, and link tables) into a new dataset with fresh UUIDs.

The copy runs entirely server-side: for every entity whose new id is referenced by
other tables we build a temporary ``(old_id, new_id)`` mapping table via
``gen_random_uuid()``, then copy each table with a single ``INSERT ... SELECT`` that
joins the maps to remap foreign keys. No rows are materialized in Python, so memory is
bounded and large (1M-10M sample) datasets are handled by the database.

This is enterprise-only and PostgreSQL-only (it relies on ``gen_random_uuid()``,
temporary tables, and statement-end FK checks). DuckDB is not supported.

New columns are copied verbatim automatically; a new *foreign-key* column must be added to
its table's ``overrides`` dict so it is remapped to the copied dataset. ``_copy_table``
asserts that every declared FK column is remapped (fails fast otherwise), and
``verify_table_coverage`` separately guards against new *tables*.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy import Table, case, func, insert, literal, text
from sqlalchemy import column as sa_column
from sqlalchemy import select as sa_select
from sqlalchemy import table as sa_table
from sqlmodel import Session, SQLModel, col, select

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
from lightly_studio.models.evaluation_annotation_metric import (
    EvaluationAnnotationMetricTable,
)
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

# Names of the temporary (old_id -> new_id) mapping tables, one per entity whose new id
# is referenced by other tables.
_MAP_COLLECTION = "deep_copy_map_collection"
_MAP_SAMPLE = "deep_copy_map_sample"
_MAP_TAG = "deep_copy_map_tag"
_MAP_OBJECT_TRACK = "deep_copy_map_object_track"
_MAP_ANNOTATION_LABEL = "deep_copy_map_annotation_label"
_MAP_EMBEDDING_MODEL = "deep_copy_map_embedding_model"
_MAP_EVALUATION_RUN = "deep_copy_map_evaluation_run"


def deep_copy(
    session: Session,
    dataset_id: UUID,
    copy_name: str,
) -> CollectionTable:
    """Deep copy a dataset with all related entities.

    Args:
        session: Database session (must be bound to PostgreSQL).
        dataset_id: Dataset ID to copy.
        copy_name: Name for the new dataset.

    Returns:
        The newly created dataset.
    """
    db_manager.require_postgres_backend(session)
    # If this fails, a new table was added. Update deep_copy to handle it, then update
    # the count in table_coverage_utils.
    table_coverage_utils.verify_table_coverage()

    new_dataset_id = uuid4()
    now = datetime.now(timezone.utc)

    # The hierarchy gives the root collection name that's needed to derive copied names.
    hierarchy = dataset_resolver.get_hierarchy(session=session, dataset_id=dataset_id)
    old_root_name = hierarchy[0].name

    # 1. New dataset row (parents must exist before their FK children).
    session.exec(insert(_table(DatasetTable)).values(dataset_id=new_dataset_id))

    # 2. Build the id maps. The 7 entities below have new ids referenced by other tables.
    _build_id_maps(session=session, old_dataset_id=dataset_id)

    # 3. Copy each table with a single INSERT ... SELECT, in FK dependency order
    #    (parents before children; PostgreSQL checks FKs at statement end).
    _copy_collections(
        session=session,
        new_dataset_id=new_dataset_id,
        copy_name=copy_name,
        old_root_name=old_root_name,
        now=now,
    )
    _copy_tags(session=session, now=now)
    _copy_object_tracks(session=session, new_dataset_id=new_dataset_id)
    _copy_annotation_labels(session=session, new_dataset_id=new_dataset_id)
    _copy_embedding_models(session=session, now=now)
    _copy_samples(session=session, now=now)
    _copy_evaluation_runs(session=session, new_dataset_id=new_dataset_id, now=now)

    _copy_images(session=session, now=now)
    _copy_videos(session=session)
    _copy_video_frames(session=session)
    _copy_groups(session=session)
    _copy_captions(session=session, now=now)
    _copy_annotations(session=session, now=now)
    _copy_annotation_details(session=session, detail_table=ObjectDetectionAnnotationTable)
    _copy_annotation_details(session=session, detail_table=SegmentationAnnotationTable)
    _copy_annotation_details(session=session, detail_table=TemporalSpanTable)

    _copy_sample_embeddings(session=session)
    _copy_metadata(session=session, now=now)
    _copy_evaluation_sample_metrics(session=session)
    _copy_evaluation_annotation_metrics(session=session)

    _copy_sample_tag_links(session=session)
    _copy_sample_group_links(session=session)
    _copy_annotation_collection_coverage(session=session)

    # Commit so the ON COMMIT DROP map tables are released and a subsequent deep_copy in
    # the same session can recreate them.
    session.commit()

    return session.exec(
        select(CollectionTable).where(
            CollectionTable.dataset_id == new_dataset_id,
            col(CollectionTable.parent_collection_id).is_(None),
        )
    ).one()


def _build_id_maps(session: Session, old_dataset_id: UUID) -> None:
    """Create the temporary (old_id -> new_id) mapping tables for the dataset."""
    dataset_params = {"old_dataset_id": old_dataset_id}
    in_collection_map = f"collection_id IN (SELECT old_id FROM {_MAP_COLLECTION})"

    _create_id_map(
        session=session,
        source_table="collection",
        id_column="collection_id",
        where_sql="dataset_id = :old_dataset_id",
        params=dataset_params,
    )
    _create_id_map(
        session=session,
        source_table="sample",
        id_column="sample_id",
        where_sql=in_collection_map,
    )
    _create_id_map(
        session=session,
        source_table="tag",
        id_column="tag_id",
        where_sql=in_collection_map,
    )
    _create_id_map(
        session=session,
        source_table="object_track",
        id_column="object_track_id",
        where_sql="dataset_id = :old_dataset_id",
        params=dataset_params,
    )
    _create_id_map(
        session=session,
        source_table="annotation_label",
        id_column="annotation_label_id",
        where_sql="dataset_id = :old_dataset_id",
        params=dataset_params,
    )
    _create_id_map(
        session=session,
        source_table="embedding_model",
        id_column="embedding_model_id",
        where_sql=in_collection_map,
    )
    _create_id_map(
        session=session,
        source_table="evaluation_run",
        id_column="id",
        where_sql=f"gt_annotation_collection_id IN (SELECT old_id FROM {_MAP_COLLECTION})",
    )


def _create_id_map(
    session: Session,
    source_table: str,
    id_column: str,
    where_sql: str,
    params: dict[str, Any] | None = None,
) -> None:
    """Create a temporary ``(old_id, new_id)`` table for in-scope rows of a source table.

    ``ON COMMIT DROP`` ties the table's lifetime to the surrounding transaction, so it is
    released on commit and never leaks onto a pooled connection. The primary key on
    ``old_id`` keeps the downstream joins fast on large datasets.

    Args:
        session: Database session.
        source_table: Table to map ids for; also determines the temp table name.
        id_column: Primary-key column whose values become ``old_id``.
        where_sql: SQL predicate selecting the in-scope rows. An internal constant; any
            values are bound through ``params``.
        params: Bind parameters referenced by ``where_sql``.
    """
    map_name = f"deep_copy_map_{source_table}"
    session.execute(
        text(
            f"CREATE TEMPORARY TABLE {map_name} ON COMMIT DROP AS "
            f"SELECT {id_column} AS old_id, gen_random_uuid() AS new_id "
            f"FROM {source_table} WHERE {where_sql}"
        ),
        params or {},
    )
    session.execute(text(f"ALTER TABLE {map_name} ADD PRIMARY KEY (old_id)"))


def _copy_table(
    session: Session,
    target: type[SQLModel],
    source: Any,
    from_clause: Any,
    overrides: dict[str, Any],
) -> None:
    """Emit ``INSERT INTO target (cols) SELECT <override|verbatim per col> FROM ...``.

    Column names come from the target table so new columns are copied verbatim
    automatically. For each column an ``overrides`` expression is selected if present,
    otherwise the source column is copied as-is. Names and select expressions are built
    from the same ordered column list, so they align positionally.

    Args:
        session: Database session.
        target: SQLModel table class to insert into.
        source: Aliased source table to select from (exposes ``.c``).
        from_clause: ``source`` joined to the map tables needed for the remaps.
        overrides: Column name -> expression to select instead of the verbatim source
            column (FK/PK remaps, fresh ``gen_random_uuid()`` ids, regenerated timestamps).
    """
    table = _table(target)
    # Every declared foreign key must be remapped; an unmapped one would be copied verbatim
    # and point back at the source dataset. Catches a new FK column on a copied table.
    unmapped_fk_columns = {c.name for c in table.columns if c.foreign_keys} - set(overrides)
    if unmapped_fk_columns:
        raise RuntimeError(
            f"{table.name}: foreign-key column(s) {sorted(unmapped_fk_columns)} are not in "
            "`overrides`; add them so they are remapped to the copied dataset."
        )
    columns = list(table.columns)
    select_exprs = [
        (
            overrides[column.name].label(column.name)
            if column.name in overrides
            else source.c[column.name]
        )
        for column in columns
    ]
    statement = sa_select(*select_exprs).select_from(from_clause)
    session.exec(insert(table).from_select([c.name for c in columns], statement))


def _map(name: str, alias: str | None = None) -> Any:
    """Return a lightweight clause for a temporary map table (columns old_id, new_id).

    Args:
        name: Temp map table name.
        alias: Optional alias, needed when the same map table is joined more than once in
            a single statement.
    """
    handle = sa_table(name, sa_column("old_id"), sa_column("new_id"))
    return handle.alias(alias) if alias is not None else handle


def _table(model: type[SQLModel]) -> Table:
    """Return the SQLAlchemy ``Table`` backing a SQLModel table class."""
    return cast(Table, model.__table__)  # type: ignore[attr-defined]


def _copy_collections(
    session: Session,
    new_dataset_id: UUID,
    copy_name: str,
    old_root_name: str,
    now: datetime,
) -> None:
    """Copy the collection hierarchy, remapping parent links and deriving names.

    The single multi-row insert satisfies the self-referential ``parent_collection_id``
    FK because PostgreSQL checks it at statement end, once all rows are present.

    Args:
        session: Database session.
        new_dataset_id: Dataset id the copied collections belong to.
        copy_name: New name for the root collection.
        old_root_name: Name of the source root, used to derive child names.
        now: Timestamp for the copied collections' created_at/updated_at.
    """
    src = _table(CollectionTable).alias("src")
    map_collection = _map(_MAP_COLLECTION)
    map_parent = _map(_MAP_COLLECTION, alias="map_parent")

    # Replace the first occurrence of the old root name with copy_name, leaving names
    # that do not contain it unchanged.
    root_pos = func.strpos(src.c["name"], literal(old_root_name))
    name_expr = case(
        (root_pos == 0, src.c["name"]),
        else_=func.left(src.c["name"], root_pos - 1)
        .concat(literal(copy_name))
        .concat(func.substr(src.c["name"], root_pos + func.length(literal(old_root_name)))),
    )
    from_clause = src.join(
        map_collection, map_collection.c.old_id == src.c["collection_id"]
    ).outerjoin(map_parent, map_parent.c.old_id == src.c["parent_collection_id"])
    overrides = {
        "collection_id": map_collection.c.new_id,
        "dataset_id": literal(new_dataset_id),
        "parent_collection_id": map_parent.c.new_id,
        "name": name_expr,
        "created_at": literal(now),
        "updated_at": literal(now),
    }
    _copy_table(
        session=session,
        target=CollectionTable,
        source=src,
        from_clause=from_clause,
        overrides=overrides,
    )


def _copy_samples(session: Session, now: datetime) -> None:
    """Copy samples, remapping collection_id."""
    src = _table(SampleTable).alias("src")
    map_sample = _map(_MAP_SAMPLE)
    map_collection = _map(_MAP_COLLECTION)
    from_clause = src.join(map_sample, map_sample.c.old_id == src.c["sample_id"]).join(
        map_collection, map_collection.c.old_id == src.c["collection_id"]
    )
    overrides = {
        "sample_id": map_sample.c.new_id,
        "collection_id": map_collection.c.new_id,
        "created_at": literal(now),
        "updated_at": literal(now),
    }
    _copy_table(
        session=session,
        target=SampleTable,
        source=src,
        from_clause=from_clause,
        overrides=overrides,
    )


def _copy_tags(session: Session, now: datetime) -> None:
    """Copy tags, remapping collection_id."""
    src = _table(TagTable).alias("src")
    map_tag = _map(_MAP_TAG)
    map_collection = _map(_MAP_COLLECTION)
    from_clause = src.join(map_tag, map_tag.c.old_id == src.c["tag_id"]).join(
        map_collection, map_collection.c.old_id == src.c["collection_id"]
    )
    overrides = {
        "tag_id": map_tag.c.new_id,
        "collection_id": map_collection.c.new_id,
        "created_at": literal(now),
        "updated_at": literal(now),
    }
    _copy_table(
        session=session,
        target=TagTable,
        source=src,
        from_clause=from_clause,
        overrides=overrides,
    )


def _copy_object_tracks(session: Session, new_dataset_id: UUID) -> None:
    """Copy object tracks, remapping dataset_id."""
    src = _table(ObjectTrackTable).alias("src")
    map_track = _map(_MAP_OBJECT_TRACK)
    from_clause = src.join(map_track, map_track.c.old_id == src.c["object_track_id"])
    overrides = {
        "object_track_id": map_track.c.new_id,
        "dataset_id": literal(new_dataset_id),
    }
    _copy_table(
        session=session,
        target=ObjectTrackTable,
        source=src,
        from_clause=from_clause,
        overrides=overrides,
    )


def _copy_annotation_labels(session: Session, new_dataset_id: UUID) -> None:
    """Copy annotation labels, remapping dataset_id.

    ``created_at`` is copied verbatim (it is a VARCHAR column, so regenerating a datetime
    literal would not match the stored representation).
    """
    src = _table(AnnotationLabelTable).alias("src")
    map_label = _map(_MAP_ANNOTATION_LABEL)
    from_clause = src.join(map_label, map_label.c.old_id == src.c["annotation_label_id"])
    overrides = {
        "annotation_label_id": map_label.c.new_id,
        "dataset_id": literal(new_dataset_id),
    }
    _copy_table(
        session=session,
        target=AnnotationLabelTable,
        source=src,
        from_clause=from_clause,
        overrides=overrides,
    )


def _copy_embedding_models(session: Session, now: datetime) -> None:
    """Copy embedding models, remapping collection_id."""
    src = _table(EmbeddingModelTable).alias("src")
    map_model = _map(_MAP_EMBEDDING_MODEL)
    map_collection = _map(_MAP_COLLECTION)
    from_clause = src.join(map_model, map_model.c.old_id == src.c["embedding_model_id"]).join(
        map_collection, map_collection.c.old_id == src.c["collection_id"]
    )
    overrides = {
        "embedding_model_id": map_model.c.new_id,
        "collection_id": map_collection.c.new_id,
        "created_at": literal(now),
    }
    _copy_table(
        session=session,
        target=EmbeddingModelTable,
        source=src,
        from_clause=from_clause,
        overrides=overrides,
    )


def _copy_evaluation_runs(session: Session, new_dataset_id: UUID, now: datetime) -> None:
    """Copy evaluation runs, remapping the dataset and collection FKs."""
    src = _table(EvaluationRunTable).alias("src")
    map_run = _map(_MAP_EVALUATION_RUN)
    map_gt = _map(_MAP_COLLECTION, alias="map_gt")
    map_pred = _map(_MAP_COLLECTION, alias="map_pred")
    from_clause = (
        src.join(map_run, map_run.c.old_id == src.c["id"])
        .join(map_gt, map_gt.c.old_id == src.c["gt_annotation_collection_id"])
        .join(map_pred, map_pred.c.old_id == src.c["pred_annotation_collection_id"])
    )
    overrides = {
        "id": map_run.c.new_id,
        "dataset_id": literal(new_dataset_id),
        "gt_annotation_collection_id": map_gt.c.new_id,
        "pred_annotation_collection_id": map_pred.c.new_id,
        "created_at": literal(now),
    }
    _copy_table(
        session=session,
        target=EvaluationRunTable,
        source=src,
        from_clause=from_clause,
        overrides=overrides,
    )


def _copy_images(session: Session, now: datetime) -> None:
    """Copy images, remapping sample_id."""
    src = _table(ImageTable).alias("src")
    map_sample = _map(_MAP_SAMPLE)
    from_clause = src.join(map_sample, map_sample.c.old_id == src.c["sample_id"])
    overrides = {
        "sample_id": map_sample.c.new_id,
        "created_at": literal(now),
        "updated_at": literal(now),
    }
    _copy_table(
        session=session,
        target=ImageTable,
        source=src,
        from_clause=from_clause,
        overrides=overrides,
    )


def _copy_videos(session: Session) -> None:
    """Copy videos, remapping sample_id."""
    src = _table(VideoTable).alias("src")
    map_sample = _map(_MAP_SAMPLE)
    from_clause = src.join(map_sample, map_sample.c.old_id == src.c["sample_id"])
    overrides = {"sample_id": map_sample.c.new_id}
    _copy_table(
        session=session,
        target=VideoTable,
        source=src,
        from_clause=from_clause,
        overrides=overrides,
    )


def _copy_video_frames(session: Session) -> None:
    """Copy video frames, remapping sample_id and parent_sample_id."""
    src = _table(VideoFrameTable).alias("src")
    map_sample = _map(_MAP_SAMPLE)
    map_parent = _map(_MAP_SAMPLE, alias="map_parent")
    from_clause = src.join(map_sample, map_sample.c.old_id == src.c["sample_id"]).join(
        map_parent, map_parent.c.old_id == src.c["parent_sample_id"]
    )
    overrides = {
        "sample_id": map_sample.c.new_id,
        "parent_sample_id": map_parent.c.new_id,
    }
    _copy_table(
        session=session,
        target=VideoFrameTable,
        source=src,
        from_clause=from_clause,
        overrides=overrides,
    )


def _copy_groups(session: Session) -> None:
    """Copy groups, remapping sample_id."""
    src = _table(GroupTable).alias("src")
    map_sample = _map(_MAP_SAMPLE)
    from_clause = src.join(map_sample, map_sample.c.old_id == src.c["sample_id"])
    overrides = {"sample_id": map_sample.c.new_id}
    _copy_table(
        session=session,
        target=GroupTable,
        source=src,
        from_clause=from_clause,
        overrides=overrides,
    )


def _copy_captions(session: Session, now: datetime) -> None:
    """Copy captions, remapping sample_id and parent_sample_id."""
    src = _table(CaptionTable).alias("src")
    map_sample = _map(_MAP_SAMPLE)
    map_parent = _map(_MAP_SAMPLE, alias="map_parent")
    from_clause = src.join(map_sample, map_sample.c.old_id == src.c["sample_id"]).join(
        map_parent, map_parent.c.old_id == src.c["parent_sample_id"]
    )
    overrides = {
        "sample_id": map_sample.c.new_id,
        "parent_sample_id": map_parent.c.new_id,
        "created_at": literal(now),
    }
    _copy_table(
        session=session,
        target=CaptionTable,
        source=src,
        from_clause=from_clause,
        overrides=overrides,
    )


def _copy_annotations(session: Session, now: datetime) -> None:
    """Copy annotation_base, remapping sample, label, and (nullable) object track FKs."""
    src = _table(AnnotationBaseTable).alias("src")
    map_sample = _map(_MAP_SAMPLE)
    map_parent = _map(_MAP_SAMPLE, alias="map_parent")
    map_label = _map(_MAP_ANNOTATION_LABEL)
    map_track = _map(_MAP_OBJECT_TRACK)
    from_clause = (
        src.join(map_sample, map_sample.c.old_id == src.c["sample_id"])
        .join(map_parent, map_parent.c.old_id == src.c["parent_sample_id"])
        .join(map_label, map_label.c.old_id == src.c["annotation_label_id"])
        .outerjoin(map_track, map_track.c.old_id == src.c["object_track_id"])
    )
    overrides = {
        "sample_id": map_sample.c.new_id,
        "parent_sample_id": map_parent.c.new_id,
        "annotation_label_id": map_label.c.new_id,
        "object_track_id": map_track.c.new_id,
        "created_at": literal(now),
    }
    _copy_table(
        session=session,
        target=AnnotationBaseTable,
        source=src,
        from_clause=from_clause,
        overrides=overrides,
    )


def _copy_annotation_details(session: Session, detail_table: type[SQLModel]) -> None:
    """Copy an annotation detail table (object detection / segmentation), remapping sample_id."""
    src = _table(detail_table).alias("src")
    map_sample = _map(_MAP_SAMPLE)
    from_clause = src.join(map_sample, map_sample.c.old_id == src.c["sample_id"])
    overrides = {"sample_id": map_sample.c.new_id}
    _copy_table(
        session=session,
        target=detail_table,
        source=src,
        from_clause=from_clause,
        overrides=overrides,
    )


def _copy_sample_embeddings(session: Session) -> None:
    """Copy sample embeddings, remapping sample_id and embedding_model_id.

    The pgvector ``embedding`` column is copied verbatim, server-side. The inner join on
    the embedding-model map drops any embedding whose model is not part of the dataset.
    """
    src = _table(SampleEmbeddingTable).alias("src")
    map_sample = _map(_MAP_SAMPLE)
    map_model = _map(_MAP_EMBEDDING_MODEL)
    from_clause = src.join(map_sample, map_sample.c.old_id == src.c["sample_id"]).join(
        map_model, map_model.c.old_id == src.c["embedding_model_id"]
    )
    overrides = {
        "sample_id": map_sample.c.new_id,
        "embedding_model_id": map_model.c.new_id,
    }
    _copy_table(
        session=session,
        target=SampleEmbeddingTable,
        source=src,
        from_clause=from_clause,
        overrides=overrides,
    )


def _copy_metadata(session: Session, now: datetime) -> None:
    """Copy sample metadata with a fresh custom_metadata_id, remapping sample_id."""
    src = _table(SampleMetadataTable).alias("src")
    map_sample = _map(_MAP_SAMPLE)
    from_clause = src.join(map_sample, map_sample.c.old_id == src.c["sample_id"])
    overrides = {
        "custom_metadata_id": func.gen_random_uuid(),
        "sample_id": map_sample.c.new_id,
        "created_at": literal(now),
        "updated_at": literal(now),
    }
    _copy_table(
        session=session,
        target=SampleMetadataTable,
        source=src,
        from_clause=from_clause,
        overrides=overrides,
    )


def _copy_evaluation_sample_metrics(session: Session) -> None:
    """Copy evaluation sample metrics, remapping evaluation_run_id and sample_id."""
    src = _table(EvaluationSampleMetricTable).alias("src")
    map_run = _map(_MAP_EVALUATION_RUN)
    map_sample = _map(_MAP_SAMPLE)
    from_clause = src.join(map_run, map_run.c.old_id == src.c["evaluation_run_id"]).join(
        map_sample, map_sample.c.old_id == src.c["sample_id"]
    )
    overrides = {
        "evaluation_run_id": map_run.c.new_id,
        "sample_id": map_sample.c.new_id,
    }
    _copy_table(
        session=session,
        target=EvaluationSampleMetricTable,
        source=src,
        from_clause=from_clause,
        overrides=overrides,
    )


def _copy_evaluation_annotation_metrics(session: Session) -> None:
    """Copy evaluation annotation metrics, remapping run/sample and nullable annotation FKs."""
    src = _table(EvaluationAnnotationMetricTable).alias("src")
    map_run = _map(_MAP_EVALUATION_RUN)
    map_sample = _map(_MAP_SAMPLE)
    map_pred = _map(_MAP_SAMPLE, alias="map_pred")
    map_gt = _map(_MAP_SAMPLE, alias="map_gt")
    from_clause = (
        src.join(map_run, map_run.c.old_id == src.c["evaluation_run_id"])
        .join(map_sample, map_sample.c.old_id == src.c["sample_id"])
        .outerjoin(map_pred, map_pred.c.old_id == src.c["pred_annotation_id"])
        .outerjoin(map_gt, map_gt.c.old_id == src.c["gt_annotation_id"])
    )
    overrides = {
        "id": func.gen_random_uuid(),
        "evaluation_run_id": map_run.c.new_id,
        "sample_id": map_sample.c.new_id,
        "pred_annotation_id": map_pred.c.new_id,
        "gt_annotation_id": map_gt.c.new_id,
    }
    _copy_table(
        session=session,
        target=EvaluationAnnotationMetricTable,
        source=src,
        from_clause=from_clause,
        overrides=overrides,
    )


def _copy_sample_tag_links(session: Session) -> None:
    """Copy sample-tag links. Inner joins drop links whose tag is out of scope."""
    src = _table(SampleTagLinkTable).alias("src")
    map_sample = _map(_MAP_SAMPLE)
    map_tag = _map(_MAP_TAG)
    from_clause = src.join(map_sample, map_sample.c.old_id == src.c["sample_id"]).join(
        map_tag, map_tag.c.old_id == src.c["tag_id"]
    )
    overrides = {
        "sample_id": map_sample.c.new_id,
        "tag_id": map_tag.c.new_id,
    }
    _copy_table(
        session=session,
        target=SampleTagLinkTable,
        source=src,
        from_clause=from_clause,
        overrides=overrides,
    )


def _copy_sample_group_links(session: Session) -> None:
    """Copy sample-group links, remapping sample_id and parent_sample_id."""
    src = _table(SampleGroupLinkTable).alias("src")
    map_sample = _map(_MAP_SAMPLE)
    map_parent = _map(_MAP_SAMPLE, alias="map_parent")
    from_clause = src.join(map_sample, map_sample.c.old_id == src.c["sample_id"]).join(
        map_parent, map_parent.c.old_id == src.c["parent_sample_id"]
    )
    overrides = {
        "sample_id": map_sample.c.new_id,
        "parent_sample_id": map_parent.c.new_id,
    }
    _copy_table(
        session=session,
        target=SampleGroupLinkTable,
        source=src,
        from_clause=from_clause,
        overrides=overrides,
    )


def _copy_annotation_collection_coverage(session: Session) -> None:
    """Copy annotation collection coverage rows, remapping collection and sample ids."""
    src = _table(AnnotationCollectionCoverageTable).alias("src")
    map_collection = _map(_MAP_COLLECTION)
    map_sample = _map(_MAP_SAMPLE)
    from_clause = src.join(
        map_collection, map_collection.c.old_id == src.c["annotation_collection_id"]
    ).join(map_sample, map_sample.c.old_id == src.c["parent_sample_id"])
    overrides = {
        "annotation_collection_id": map_collection.c.new_id,
        "parent_sample_id": map_sample.c.new_id,
    }
    _copy_table(
        session=session,
        target=AnnotationCollectionCoverageTable,
        source=src,
        from_clause=from_clause,
        overrides=overrides,
    )
