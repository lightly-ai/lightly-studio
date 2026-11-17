"""The users of an enterprise deployment.

The auth service owns the `auth.users` table in the Studio database. Studio only reads it.
"""

from __future__ import annotations

from enum import Enum

from sqlalchemy.orm import registry
from sqlmodel import Field, SQLModel


class Role(str, Enum):
    """The role of a user. Each role includes the permissions of the roles before it."""

    VIEWER = "viewer"
    LABELER = "labeler"
    EDITOR = "editor"
    ADMIN = "admin"


class UserStatus(str, Enum):
    """The lifecycle status of a user."""

    PENDING = "pending"
    ACTIVE = "active"
    INACTIVE = "inactive"


class AuthSQLModel(SQLModel, registry=registry()):
    """The base of the tables that the auth service owns.

    The tables have their own metadata. Studio's schema creation, schema drops, Alembic
    migrations and table checks use `SQLModel.metadata` and thus never change these tables.
    """


class UserTable(AuthSQLModel, table=True):
    """A user of an enterprise deployment, as the auth service stores it.

    The table has more columns. This model maps only the columns that Studio reads.
    """

    __tablename__ = "users"
    __table_args__ = {"schema": "auth"}

    # Studio never inserts users, so the key needs no sequence.
    id: int = Field(primary_key=True, sa_column_kwargs={"autoincrement": False})
    email: str
    role: str
    status: str


class UserView(SQLModel):
    """A user, as the API returns it."""

    id: int
    email: str
    role: Role
    status: UserStatus
