"""End-to-end round-trip test for the Postgres-only deep_copy / delete_dataset pair.

Builds a richly populated dataset, deep-copies it, and deletes the copy, asserting:
- the copy is a faithful clone (identical per-table row counts, fresh IDs);
- deleting the copy removes every handled table's rows for that dataset;
- a sibling dataset and the original are left completely untouched.
"""

from typing import Any
from uuid import UUID

import pytest
from sqlmodel import Session, col, func, select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable, AnnotationType
from lightly_studio.models.annotation.object_detection import ObjectDetectionAnnotationTable
from lightly_studio.models.annotation.object_track import ObjectTrackCreate, ObjectTrackTable
from lightly_studio.models.annotation.segmentation import SegmentationAnnotationTable
from lightly_studio.models.annotation_collection_coverage import AnnotationCollectionCoverageTable
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.caption import CaptionTable
from lightly_studio.models.collection import CollectionTable
from lightly_studio.models.dataset import DatasetTable
from lightly_studio.models.embedding_model import EmbeddingModelTable
from lightly_studio.models.evaluation_annotation_metric import EvaluationAnnotationMetricTable
from lightly_studio.models.evaluation_run import EvaluationRunTable
from lightly_studio.models.evaluation_sample_metric import (
    EvaluationSampleMetricCreate,
    EvaluationSampleMetricTable,
)
from lightly_studio.models.group import GroupTable, SampleGroupLinkTable
from lightly_studio.models.image import ImageTable
from lightly_studio.models.metadata import SampleMetadataTable
from lightly_studio.models.sample import SampleTable, SampleTagLinkTable
from lightly_studio.models.sample_embedding import SampleEmbeddingTable
from lightly_studio.models.tag import TagTable
from lightly_studio.models.video import VideoFrameTable, VideoTable
from lightly_studio.resolvers import (
    dataset_resolver,
    evaluation_sample_metric_resolver,
    object_track_resolver,
    tag_resolver,
)
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_caption,
    create_collection,
    create_embedding_model,
    create_image,
    create_sample_embedding,
    create_tag,
)
from tests.resolvers.evaluation_sample_metric_resolver import (
    helpers as evaluation_sample_metric_helpers,
)
from tests.resolvers.evaluation_sample_metric_resolver.helpers import (
    TruePositiveMetricStub,
    create_annotation_metrics,
)

# Both operations are enterprise-only and PostgreSQL-backed.
pytestmark = pytest.mark.postgres_only


def _dataset_table_counts(session: Session, dataset_id: UUID) -> dict[str, int]:
    """Count rows in every handled table belonging to ``dataset_id`` (delete_dataset scoping)."""
    collection_ids = select(CollectionTable.collection_id).where(
        col(CollectionTable.dataset_id) == dataset_id
    )
    sample_ids = select(SampleTable.sample_id).where(
        col(SampleTable.collection_id).in_(collection_ids)
    )
    run_ids = select(EvaluationRunTable.id).where(
        col(EvaluationRunTable.gt_annotation_collection_id).in_(collection_ids)
    )

    def count(model: Any, where: Any) -> int:
        return session.exec(select(func.count()).select_from(model).where(where)).one()

    return {
        "collection": count(CollectionTable, col(CollectionTable.dataset_id) == dataset_id),
        "sample": count(SampleTable, col(SampleTable.sample_id).in_(sample_ids)),
        "image": count(ImageTable, col(ImageTable.sample_id).in_(sample_ids)),
        "video": count(VideoTable, col(VideoTable.sample_id).in_(sample_ids)),
        "video_frame": count(VideoFrameTable, col(VideoFrameTable.sample_id).in_(sample_ids)),
        "group": count(GroupTable, col(GroupTable.sample_id).in_(sample_ids)),
        "annotation_base": count(
            AnnotationBaseTable, col(AnnotationBaseTable.sample_id).in_(sample_ids)
        ),
        "object_detection": count(
            ObjectDetectionAnnotationTable,
            col(ObjectDetectionAnnotationTable.sample_id).in_(sample_ids),
        ),
        "segmentation": count(
            SegmentationAnnotationTable, col(SegmentationAnnotationTable.sample_id).in_(sample_ids)
        ),
        "caption": count(CaptionTable, col(CaptionTable.sample_id).in_(sample_ids)),
        "sample_embedding": count(
            SampleEmbeddingTable, col(SampleEmbeddingTable.sample_id).in_(sample_ids)
        ),
        "metadata": count(SampleMetadataTable, col(SampleMetadataTable.sample_id).in_(sample_ids)),
        "sample_tag_link": count(
            SampleTagLinkTable, col(SampleTagLinkTable.sample_id).in_(sample_ids)
        ),
        "sample_group_link": count(
            SampleGroupLinkTable, col(SampleGroupLinkTable.sample_id).in_(sample_ids)
        ),
        "tag": count(TagTable, col(TagTable.collection_id).in_(collection_ids)),
        "embedding_model": count(
            EmbeddingModelTable, col(EmbeddingModelTable.collection_id).in_(collection_ids)
        ),
        "annotation_collection_coverage": count(
            AnnotationCollectionCoverageTable,
            col(AnnotationCollectionCoverageTable.annotation_collection_id).in_(collection_ids),
        ),
        "annotation_label": count(
            AnnotationLabelTable, col(AnnotationLabelTable.dataset_id) == dataset_id
        ),
        "object_track": count(ObjectTrackTable, col(ObjectTrackTable.dataset_id) == dataset_id),
        "evaluation_run": count(
            EvaluationRunTable,
            col(EvaluationRunTable.gt_annotation_collection_id).in_(collection_ids),
        ),
        "evaluation_sample_metric": count(
            EvaluationSampleMetricTable,
            col(EvaluationSampleMetricTable.evaluation_run_id).in_(run_ids),
        ),
        "evaluation_annotation_metric": count(
            EvaluationAnnotationMetricTable,
            col(EvaluationAnnotationMetricTable.evaluation_run_id).in_(run_ids),
        ),
        "dataset": count(DatasetTable, col(DatasetTable.dataset_id) == dataset_id),
    }


def _build_full_dataset(session: Session, name: str) -> UUID:
    """Create a dataset populated across most handled tables; return its dataset id."""
    root = create_collection(session=session, collection_name=name)
    img1 = create_image(
        session=session, collection_id=root.collection_id, file_path_abs=f"/{name}/a.png"
    )
    img2 = create_image(
        session=session, collection_id=root.collection_id, file_path_abs=f"/{name}/b.png"
    )

    # metadata
    img1.sample["temperature"] = 25
    img1.sample["location"] = "city"

    # embedding model + embeddings
    model = create_embedding_model(
        session=session,
        collection_id=root.collection_id,
        embedding_model_name=f"{name}_model",
        embedding_dimension=3,
    )
    create_sample_embedding(
        session=session,
        sample_id=img1.sample_id,
        embedding_model_id=model.embedding_model_id,
        embedding=[1.0, 2.0, 3.0],
    )
    create_sample_embedding(
        session=session,
        sample_id=img2.sample_id,
        embedding_model_id=model.embedding_model_id,
        embedding=[4.0, 5.0, 6.0],
    )

    # tag + sample link + caption
    tag = create_tag(session=session, collection_id=root.collection_id, tag_name=f"{name}_tag")
    tag_resolver.add_tag_to_sample(session=session, tag_id=tag.tag_id, sample=img1.sample)
    create_caption(
        session=session, collection_id=root.collection_id, parent_sample_id=img1.sample_id
    )

    # annotations: classification, object detection (+ object track), segmentation
    label = create_annotation_label(
        session=session, root_collection_id=root.collection_id, label_name=f"{name}_label"
    )
    (track_id,) = object_track_resolver.create_many(
        session=session,
        tracks=[ObjectTrackCreate(object_track_number=1, dataset_id=root.dataset_id)],
    )
    create_annotation(
        session=session,
        collection_id=root.collection_id,
        sample_id=img1.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.CLASSIFICATION,
    )
    create_annotation(
        session=session,
        collection_id=root.collection_id,
        sample_id=img1.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.OBJECT_DETECTION,
        annotation_data={"x": 10, "y": 20, "width": 30, "height": 40, "object_track_id": track_id},
    )
    create_annotation(
        session=session,
        collection_id=root.collection_id,
        sample_id=img2.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.SEGMENTATION_MASK,
        annotation_data={
            "x": 2,
            "y": 4,
            "width": 6,
            "height": 8,
            "segmentation_mask": [1, 0, 0, 1],
        },
    )

    # evaluation run + sample metric + annotation metric (gt/pred annotations)
    run = evaluation_sample_metric_helpers.create_run(
        session=session, collection_id=root.collection_id
    )
    eval_image = create_image(session=session, collection_id=root.collection_id)
    evaluation_sample_metric_resolver.create_many(
        session=session,
        records=[
            EvaluationSampleMetricCreate(
                evaluation_run_id=run.id,
                sample_id=eval_image.sample_id,
                metric_name="precision",
                value=0.9,
            )
        ],
    )
    create_annotation_metrics(
        session=session,
        run_id=run.id,
        true_positive_metric_stubs=[
            TruePositiveMetricStub(
                sample_id=eval_image.sample_id,
                metrics={"iou": 0.8},
                gt_annotation_label_id=label.annotation_label_id,
            )
        ],
    )
    return root.dataset_id


def test_deep_copy_then_delete_round_trip(db_session: Session) -> None:
    # Arrange - a richly populated dataset plus an untouched sibling.
    original_id = _build_full_dataset(session=db_session, name="roundtrip_original")
    sibling_id = _build_full_dataset(session=db_session, name="roundtrip_sibling")

    original_counts = _dataset_table_counts(db_session, original_id)
    sibling_counts = _dataset_table_counts(db_session, sibling_id)

    # Sanity - the builder actually populated the representative tables we rely on.
    for table in (
        "sample",
        "image",
        "annotation_base",
        "object_detection",
        "segmentation",
        "caption",
        "sample_embedding",
        "metadata",
        "tag",
        "sample_tag_link",
        "embedding_model",
        "annotation_label",
        "object_track",
        "evaluation_run",
        "evaluation_sample_metric",
        "evaluation_annotation_metric",
    ):
        assert original_counts[table] > 0, f"builder did not populate {table}"

    # Act 1 - deep copy. Capture the id before delete_dataset's commit expires the ORM object.
    copy = dataset_resolver.deep_copy(
        session=db_session, dataset_id=original_id, copy_name="roundtrip_copy"
    )
    copy_id = copy.dataset_id

    # Assert - faithful clone: identical per-table counts, distinct dataset.
    assert copy_id != original_id
    assert _dataset_table_counts(db_session, copy_id) == original_counts

    # Act 2 - delete the copy.
    dataset_resolver.delete_dataset(session=db_session, dataset_id=copy_id)

    # Assert - every handled table is empty for the deleted copy.
    after = _dataset_table_counts(db_session, copy_id)
    assert all(value == 0 for value in after.values()), after

    # Assert - the original and the sibling are completely untouched.
    assert _dataset_table_counts(db_session, original_id) == original_counts
    assert _dataset_table_counts(db_session, sibling_id) == sibling_counts
