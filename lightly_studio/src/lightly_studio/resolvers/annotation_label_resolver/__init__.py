"""Handler for database operations related to annotation labels."""

from .create import create
from .delete import delete
from .get_all import (
    get_all,
    get_all_legacy,
    get_all_sorted_alphabetically,
    get_all_sorted_alphabetically_legacy,
)
from .get_by_id import get_by_id
from .get_by_ids import get_by_ids
from .get_by_label_name import get_by_label_name, get_by_label_name_legacy
from .names_by_ids import names_by_ids
from .update import update

__all__ = [
    "create",
    "delete",
    "get_all",
    "get_all_legacy",
    "get_all_sorted_alphabetically",
    "get_all_sorted_alphabetically_legacy",
    "get_by_id",
    "get_by_ids",
    "get_by_label_name",
    "get_by_label_name_legacy",
    "names_by_ids",
    "update",
]
