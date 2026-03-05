"""This module contains the Dataset model."""

from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class DatasetTable(SQLModel, table=True):
    """This class defines the Dataset model."""

    __tablename__ = "dataset"
    dataset_id: UUID = Field(default_factory=uuid4, primary_key=True)
    root_collection_id: UUID = Field()
