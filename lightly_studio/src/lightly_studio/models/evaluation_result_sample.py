"""Persisted sample snapshot for one evaluation run."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Field, SQLModel


class EvaluationResultSampleTable(SQLModel, table=True):
    """One row per sample that was included in an evaluation run."""

    __tablename__ = "evaluation_result_sample"

    evaluation_result_id: UUID = Field(foreign_key="evaluation_result.id", primary_key=True)
    sample_id: UUID = Field(foreign_key="sample.sample_id", primary_key=True, index=True)
