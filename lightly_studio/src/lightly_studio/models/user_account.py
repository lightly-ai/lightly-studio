"""The table of the users of a deployment."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Field, SQLModel


class UserAccountTable(SQLModel, table=True):
    """A user. A table that refers to a user has a foreign key to `user_id`.

    LightlyStudio does not write rows to this table.

    Attributes:
        user_id: The id of the user.
    """

    __tablename__ = "user_account"

    user_id: UUID = Field(primary_key=True)
