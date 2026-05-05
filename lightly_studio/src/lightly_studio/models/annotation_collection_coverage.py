"""Tracks which parent samples a given annotation collection (run) was applied to.

Coverage is append-only at the resolver layer: deleting an annotation does not
remove the corresponding coverage row, because coverage records "the run was
applied to this sample" independent of whether any detection survived.
"""

from uuid import UUID

from sqlmodel import Field, SQLModel


class AnnotationCollectionCoverageTable(SQLModel, table=True):
    """Join table: explicit (annotation_collection, parent_sample) membership.

    The composite primary key enforces that each (annotation_collection_id,
    parent_sample_id) pair appears at most once.
    """

    __tablename__ = "annotation_collection_coverage"

    annotation_collection_id: UUID = Field(foreign_key="collection.collection_id", primary_key=True)
    parent_sample_id: UUID = Field(foreign_key="sample.sample_id", primary_key=True)
