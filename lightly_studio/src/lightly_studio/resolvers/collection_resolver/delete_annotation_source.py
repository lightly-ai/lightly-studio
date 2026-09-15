"""Delete an annotation source and the data that depends on it."""

from uuid import UUID

from sqlalchemy import or_
from sqlmodel import Session, col, delete, select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.annotation.object_detection import ObjectDetectionAnnotationTable
from lightly_studio.models.annotation.segmentation import SegmentationAnnotationTable
from lightly_studio.models.annotation_collection_coverage import AnnotationCollectionCoverageTable
from lightly_studio.models.collection import CollectionTable
from lightly_studio.models.collection_embedding_model import CollectionEmbeddingModelTable
from lightly_studio.models.evaluation_annotation_metric import EvaluationAnnotationMetricTable
from lightly_studio.models.evaluation_run import EvaluationRunTable
from lightly_studio.models.evaluation_sample_metric import EvaluationSampleMetricTable
from lightly_studio.models.export_job import ExportJobTable
from lightly_studio.models.group import SampleGroupLinkTable
from lightly_studio.models.metadata import SampleMetadataTable
from lightly_studio.models.sample import SampleTable, SampleTagLinkTable
from lightly_studio.models.sample_embedding import SampleEmbeddingTable
from lightly_studio.models.sequence import SampleSequenceLinkTable
from lightly_studio.models.tag import TagTable
from lightly_studio.models.temporal_span import TemporalSpanTable


def delete_annotation_source(session: Session, collection: CollectionTable) -> None:
    """Delete source annotations, coverage and dependent data, retaining parent samples."""
    collection_id = collection.collection_id
    _delete_evaluations(session=session, collection_id=collection_id)
    _finish_dependency_stage(session=session)
    _delete_sample_attachments(session=session, collection_id=collection_id)
    _finish_dependency_stage(session=session)
    sample_ids = select(SampleTable.sample_id).where(SampleTable.collection_id == collection_id)
    session.exec(
        delete(AnnotationBaseTable).where(col(AnnotationBaseTable.sample_id).in_(sample_ids))
    )
    _finish_dependency_stage(session=session)
    session.exec(delete(SampleTable).where(SampleTable.collection_id == collection_id))
    _delete_collection_attachments(session=session, collection_id=collection_id)
    _finish_dependency_stage(session=session)
    session.delete(collection)
    session.commit()


def _delete_evaluations(session: Session, collection_id: UUID) -> None:
    run_ids = select(EvaluationRunTable.id).where(
        or_(
            EvaluationRunTable.gt_annotation_collection_id == collection_id,
            EvaluationRunTable.pred_annotation_collection_id == collection_id,
        )
    )
    session.exec(
        delete(EvaluationAnnotationMetricTable).where(
            col(EvaluationAnnotationMetricTable.evaluation_run_id).in_(run_ids)
        )
    )
    session.exec(
        delete(EvaluationSampleMetricTable).where(
            col(EvaluationSampleMetricTable.evaluation_run_id).in_(run_ids)
        )
    )
    _finish_dependency_stage(session=session)
    session.exec(delete(EvaluationRunTable).where(col(EvaluationRunTable.id).in_(run_ids)))


def _delete_sample_attachments(session: Session, collection_id: UUID) -> None:
    sample_ids = select(SampleTable.sample_id).where(SampleTable.collection_id == collection_id)
    for table in (
        ObjectDetectionAnnotationTable,
        SegmentationAnnotationTable,
        TemporalSpanTable,
        SampleTagLinkTable,
        SampleEmbeddingTable,
        SampleMetadataTable,
        SampleGroupLinkTable,
        SampleSequenceLinkTable,
    ):
        session.exec(delete(table).where(col(table.sample_id).in_(sample_ids)))
    session.exec(
        delete(AnnotationCollectionCoverageTable).where(
            or_(
                AnnotationCollectionCoverageTable.annotation_collection_id == collection_id,
                col(AnnotationCollectionCoverageTable.parent_sample_id).in_(sample_ids),
            )
        )
    )


def _delete_collection_attachments(session: Session, collection_id: UUID) -> None:
    tag_ids = select(TagTable.tag_id).where(TagTable.collection_id == collection_id)
    session.exec(delete(SampleTagLinkTable).where(col(SampleTagLinkTable.tag_id).in_(tag_ids)))
    _finish_dependency_stage(session=session)
    for table in (CollectionEmbeddingModelTable, ExportJobTable, TagTable):
        session.exec(delete(table).where(table.collection_id == collection_id))


def _finish_dependency_stage(session: Session) -> None:
    # DuckDB retains foreign-key references until commit, even after deleting child rows.
    if session.get_bind().dialect.name == "duckdb":
        session.commit()
