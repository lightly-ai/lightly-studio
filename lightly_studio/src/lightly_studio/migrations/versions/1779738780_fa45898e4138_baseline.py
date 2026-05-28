"""Baseline schema for PostgreSQL.

Revision ID: fa45898e4138
Revises:
Create Date: 2026-05-25 22:53:00.964497

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlmodel.sql.sqltypes import AutoString

# revision identifiers, used by Alembic.
revision: str = "fa45898e4138"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "dataset",
        sa.Column("dataset_id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("dataset_id"),
    )
    op.create_table(
        "setting",
        sa.Column(
            "grid_view_sample_rendering",
            sa.Enum("COVER", "CONTAIN", name="gridviewsamplerenderingtype"),
            nullable=False,
        ),
        sa.Column(
            "grid_view_thumbnail_quality",
            sa.Enum("RAW", "HIGH", name="gridviewthumbnailqualitytype"),
            nullable=False,
        ),
        sa.Column("key_hide_annotations", AutoString(), nullable=False),
        sa.Column("key_go_back", AutoString(), nullable=False),
        sa.Column("key_toggle_edit_mode", AutoString(), nullable=False),
        sa.Column("show_annotation_text_labels", sa.Boolean(), nullable=False),
        sa.Column("show_sample_filenames", sa.Boolean(), nullable=False),
        sa.Column("show_bounding_boxes_for_segmentation", sa.Boolean(), nullable=False),
        sa.Column("key_toolbar_selection", AutoString(), nullable=False),
        sa.Column("key_toolbar_drag", AutoString(), nullable=False),
        sa.Column("key_toolbar_bounding_box", AutoString(), nullable=False),
        sa.Column("key_toolbar_segmentation_mask", AutoString(), nullable=False),
        sa.Column("key_toolbar_brush", AutoString(), nullable=False),
        sa.Column("key_toolbar_eraser", AutoString(), nullable=False),
        sa.Column("setting_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("setting_id"),
    )
    op.create_index(op.f("ix_setting_created_at"), "setting", ["created_at"], unique=False)
    op.create_table(
        "tag",
        sa.Column("name", AutoString(), nullable=False),
        sa.Column("tag_id", sa.Uuid(), nullable=False),
        sa.Column("collection_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("tag_id"),
        sa.UniqueConstraint("collection_id", "kind", "name", name="unique_name_constraint"),
    )
    op.create_index(op.f("ix_tag_created_at"), "tag", ["created_at"], unique=False)
    op.create_table(
        "two_dim_embeddings",
        sa.Column("hash", AutoString(), nullable=False),
        sa.Column("x", sa.ARRAY(sa.Float()), nullable=True),
        sa.Column("y", sa.ARRAY(sa.Float()), nullable=True),
        sa.PrimaryKeyConstraint("hash"),
    )
    op.create_table(
        "annotation_label",
        sa.Column("dataset_id", sa.Uuid(), nullable=False),
        sa.Column("annotation_label_name", AutoString(), nullable=False),
        sa.Column("annotation_label_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", AutoString(), nullable=False),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["dataset.dataset_id"],
        ),
        sa.PrimaryKeyConstraint("annotation_label_id"),
        sa.UniqueConstraint("annotation_label_name", "dataset_id"),
    )
    op.create_index(
        op.f("ix_annotation_label_created_at"), "annotation_label", ["created_at"], unique=False
    )
    op.create_index(
        op.f("ix_annotation_label_dataset_id"), "annotation_label", ["dataset_id"], unique=False
    )
    op.create_table(
        "collection",
        sa.Column("name", AutoString(), nullable=False),
        sa.Column("parent_collection_id", sa.Uuid(), nullable=True),
        sa.Column(
            "sample_type",
            sa.Enum(
                "VIDEO", "VIDEO_FRAME", "IMAGE", "ANNOTATION", "CAPTION", "GROUP", name="sampletype"
            ),
            nullable=False,
        ),
        sa.Column("group_component_name", AutoString(), nullable=True),
        sa.Column("group_component_index", sa.Integer(), nullable=True),
        sa.Column("collection_id", sa.Uuid(), nullable=False),
        sa.Column("dataset_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["dataset.dataset_id"],
        ),
        sa.ForeignKeyConstraint(
            ["parent_collection_id"],
            ["collection.collection_id"],
        ),
        sa.PrimaryKeyConstraint("collection_id"),
        sa.UniqueConstraint("name", "parent_collection_id", name="unique_collection"),
    )
    op.create_index(op.f("ix_collection_created_at"), "collection", ["created_at"], unique=False)
    op.create_index(op.f("ix_collection_dataset_id"), "collection", ["dataset_id"], unique=False)
    op.create_index(op.f("ix_collection_name"), "collection", ["name"], unique=False)
    op.create_index(
        op.f("ix_collection_parent_collection_id"),
        "collection",
        ["parent_collection_id"],
        unique=False,
    )
    op.create_table(
        "object_track",
        sa.Column("object_track_id", sa.Uuid(), nullable=False),
        sa.Column("object_track_number", sa.Integer(), nullable=False),
        sa.Column("dataset_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["dataset.dataset_id"],
        ),
        sa.PrimaryKeyConstraint("object_track_id"),
    )
    op.create_table(
        "embedding_model",
        sa.Column("name", AutoString(), nullable=False),
        sa.Column("parameter_count_in_mb", sa.Integer(), nullable=True),
        sa.Column("embedding_model_hash", sa.VARCHAR(length=128), nullable=True),
        sa.Column("embedding_dimension", sa.Integer(), nullable=False),
        sa.Column("collection_id", sa.Uuid(), nullable=False),
        sa.Column("embedding_model_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["collection_id"],
            ["collection.collection_id"],
        ),
        sa.PrimaryKeyConstraint("embedding_model_id"),
    )
    op.create_index(
        op.f("ix_embedding_model_created_at"), "embedding_model", ["created_at"], unique=False
    )
    op.create_table(
        "evaluation_run",
        sa.Column("name", AutoString(), nullable=False),
        sa.Column("gt_annotation_collection_id", sa.Uuid(), nullable=False),
        sa.Column("pred_annotation_collection_id", sa.Uuid(), nullable=False),
        sa.Column(
            "task_type",
            sa.Enum(
                "OBJECT_DETECTION",
                "CLASSIFICATION",
                "INSTANCE_SEGMENTATION",
                name="evaluationtasktype",
            ),
            nullable=False,
        ),
        sa.Column("config_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["gt_annotation_collection_id"],
            ["collection.collection_id"],
        ),
        sa.ForeignKeyConstraint(
            ["pred_annotation_collection_id"],
            ["collection.collection_id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "sample",
        sa.Column("collection_id", sa.Uuid(), nullable=False),
        sa.Column("sample_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["collection_id"],
            ["collection.collection_id"],
        ),
        sa.PrimaryKeyConstraint("sample_id"),
    )
    op.create_index(op.f("ix_sample_created_at"), "sample", ["created_at"], unique=False)
    op.create_table(
        "annotation_base",
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("sample_id", sa.Uuid(), nullable=False),
        sa.Column(
            "annotation_type",
            sa.Enum(
                "CLASSIFICATION", "SEGMENTATION_MASK", "OBJECT_DETECTION", name="annotationtype"
            ),
            nullable=False,
        ),
        sa.Column("annotation_label_id", sa.Uuid(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("parent_sample_id", sa.Uuid(), nullable=False),
        sa.Column("object_track_id", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(
            ["annotation_label_id"],
            ["annotation_label.annotation_label_id"],
        ),
        sa.ForeignKeyConstraint(
            ["object_track_id"],
            ["object_track.object_track_id"],
        ),
        sa.ForeignKeyConstraint(
            ["parent_sample_id"],
            ["sample.sample_id"],
        ),
        sa.ForeignKeyConstraint(
            ["sample_id"],
            ["sample.sample_id"],
        ),
        sa.PrimaryKeyConstraint("sample_id"),
    )
    op.create_index(
        op.f("ix_annotation_base_created_at"), "annotation_base", ["created_at"], unique=False
    )
    op.create_table(
        "annotation_collection_coverage",
        sa.Column("annotation_collection_id", sa.Uuid(), nullable=False),
        sa.Column("parent_sample_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["annotation_collection_id"],
            ["collection.collection_id"],
        ),
        sa.ForeignKeyConstraint(
            ["parent_sample_id"],
            ["sample.sample_id"],
        ),
        sa.PrimaryKeyConstraint("annotation_collection_id", "parent_sample_id"),
    )
    op.create_table(
        "caption",
        sa.Column("sample_id", sa.Uuid(), nullable=False),
        sa.Column("parent_sample_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("text", AutoString(), nullable=False),
        sa.ForeignKeyConstraint(
            ["parent_sample_id"],
            ["sample.sample_id"],
        ),
        sa.ForeignKeyConstraint(
            ["sample_id"],
            ["sample.sample_id"],
        ),
        sa.PrimaryKeyConstraint("sample_id"),
    )
    op.create_index(op.f("ix_caption_created_at"), "caption", ["created_at"], unique=False)
    op.create_table(
        "evaluation_sample_metric",
        sa.Column("evaluation_run_id", sa.Uuid(), nullable=False),
        sa.Column("sample_id", sa.Uuid(), nullable=False),
        sa.Column("metric_name", AutoString(), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(
            ["evaluation_run_id"],
            ["evaluation_run.id"],
        ),
        sa.ForeignKeyConstraint(
            ["sample_id"],
            ["sample.sample_id"],
        ),
        sa.PrimaryKeyConstraint("evaluation_run_id", "sample_id", "metric_name"),
    )
    op.create_index(
        op.f("ix_evaluation_sample_metric_evaluation_run_id"),
        "evaluation_sample_metric",
        ["evaluation_run_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_evaluation_sample_metric_sample_id"),
        "evaluation_sample_metric",
        ["sample_id"],
        unique=False,
    )
    op.create_table(
        "group",
        sa.Column("sample_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["sample_id"],
            ["sample.sample_id"],
        ),
        sa.PrimaryKeyConstraint("sample_id"),
    )
    op.create_table(
        "image",
        sa.Column("file_name", AutoString(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("file_path_abs", AutoString(), nullable=False),
        sa.Column("sample_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["sample_id"],
            ["sample.sample_id"],
        ),
        sa.PrimaryKeyConstraint("sample_id"),
    )
    op.create_index(op.f("ix_image_created_at"), "image", ["created_at"], unique=False)
    op.create_table(
        "metadata",
        sa.Column("custom_metadata_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("metadata_schema", sa.JSON(), nullable=False),
        sa.Column("sample_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["sample_id"],
            ["sample.sample_id"],
        ),
        sa.PrimaryKeyConstraint("custom_metadata_id"),
        sa.UniqueConstraint("sample_id"),
    )
    op.create_table(
        "sample_embedding",
        sa.Column("sample_id", sa.Uuid(), nullable=False),
        sa.Column("embedding_model_id", sa.Uuid(), nullable=False),
        sa.Column("embedding", Vector(), nullable=True),
        sa.ForeignKeyConstraint(
            ["embedding_model_id"],
            ["embedding_model.embedding_model_id"],
        ),
        sa.ForeignKeyConstraint(
            ["sample_id"],
            ["sample.sample_id"],
        ),
        sa.PrimaryKeyConstraint("sample_id", "embedding_model_id"),
    )
    op.create_table(
        "sampletaglinktable",
        sa.Column("sample_id", sa.Uuid(), nullable=False),
        sa.Column("tag_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["sample_id"],
            ["sample.sample_id"],
        ),
        sa.ForeignKeyConstraint(
            ["tag_id"],
            ["tag.tag_id"],
        ),
        sa.PrimaryKeyConstraint("sample_id", "tag_id"),
    )
    op.create_table(
        "video",
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("duration_s", sa.Float(), nullable=True),
        sa.Column("fps", sa.Float(), nullable=False),
        sa.Column("file_name", AutoString(), nullable=False),
        sa.Column("file_path_abs", AutoString(), nullable=False),
        sa.Column("sample_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["sample_id"],
            ["sample.sample_id"],
        ),
        sa.PrimaryKeyConstraint("sample_id"),
    )
    op.create_table(
        "evaluation_annotation_metric",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("evaluation_run_id", sa.Uuid(), nullable=False),
        sa.Column("sample_id", sa.Uuid(), nullable=False),
        sa.Column("pred_annotation_id", sa.Uuid(), nullable=True),
        sa.Column("gt_annotation_id", sa.Uuid(), nullable=True),
        sa.Column("metric_name", AutoString(), nullable=True),
        sa.Column("value", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(
            ["evaluation_run_id"],
            ["evaluation_run.id"],
        ),
        sa.ForeignKeyConstraint(
            ["gt_annotation_id"],
            ["annotation_base.sample_id"],
        ),
        sa.ForeignKeyConstraint(
            ["pred_annotation_id"],
            ["annotation_base.sample_id"],
        ),
        sa.ForeignKeyConstraint(
            ["sample_id"],
            ["sample.sample_id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_evaluation_annotation_metric_evaluation_run_id"),
        "evaluation_annotation_metric",
        ["evaluation_run_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_evaluation_annotation_metric_gt_annotation_id"),
        "evaluation_annotation_metric",
        ["gt_annotation_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_evaluation_annotation_metric_metric_name"),
        "evaluation_annotation_metric",
        ["metric_name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_evaluation_annotation_metric_pred_annotation_id"),
        "evaluation_annotation_metric",
        ["pred_annotation_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_evaluation_annotation_metric_sample_id"),
        "evaluation_annotation_metric",
        ["sample_id"],
        unique=False,
    )
    op.create_table(
        "object_detection_annotation",
        sa.Column("sample_id", sa.Uuid(), nullable=False),
        sa.Column("x", sa.Integer(), nullable=False),
        sa.Column("y", sa.Integer(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["sample_id"],
            ["annotation_base.sample_id"],
        ),
        sa.PrimaryKeyConstraint("sample_id"),
    )
    op.create_table(
        "samplegrouplinktable",
        sa.Column("sample_id", sa.Uuid(), nullable=False),
        sa.Column("parent_sample_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["parent_sample_id"],
            ["group.sample_id"],
        ),
        sa.ForeignKeyConstraint(
            ["sample_id"],
            ["sample.sample_id"],
        ),
        sa.PrimaryKeyConstraint("sample_id"),
    )
    op.create_table(
        "segmentation_annotation",
        sa.Column("sample_id", sa.Uuid(), nullable=False),
        sa.Column("x", sa.Integer(), nullable=False),
        sa.Column("y", sa.Integer(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("segmentation_mask", sa.ARRAY(sa.Integer()), nullable=True),
        sa.ForeignKeyConstraint(
            ["sample_id"],
            ["annotation_base.sample_id"],
        ),
        sa.PrimaryKeyConstraint("sample_id"),
    )
    op.create_table(
        "video_frame",
        sa.Column("frame_number", sa.Integer(), nullable=False),
        sa.Column("frame_timestamp_pts", sa.Integer(), nullable=False),
        sa.Column("frame_timestamp_s", sa.Float(), nullable=False),
        sa.Column("parent_sample_id", sa.Uuid(), nullable=False),
        sa.Column("rotation_deg", sa.Integer(), nullable=False),
        sa.Column("sample_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["parent_sample_id"],
            ["video.sample_id"],
        ),
        sa.ForeignKeyConstraint(
            ["sample_id"],
            ["sample.sample_id"],
        ),
        sa.PrimaryKeyConstraint("sample_id"),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Baseline has no prior revision; downgrading is not supported."""
    raise NotImplementedError("Cannot downgrade below the initial schema revision.")
