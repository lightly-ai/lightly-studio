"""Handler for database operations related to tags."""

from lightly_studio.resolvers.tag_resolver.add_sample_ids_to_tag_id import (
    add_sample_ids_to_tag_id,
)
from lightly_studio.resolvers.tag_resolver.add_samples_to_tag_from_query import (
    add_samples_to_tag_from_query,
)
from lightly_studio.resolvers.tag_resolver.add_tag_to_sample import add_tag_to_sample
from lightly_studio.resolvers.tag_resolver.create import create
from lightly_studio.resolvers.tag_resolver.delete import delete
from lightly_studio.resolvers.tag_resolver.get_all_by_collection_id import (
    get_all_by_collection_id,
)
from lightly_studio.resolvers.tag_resolver.get_by_id import get_by_id
from lightly_studio.resolvers.tag_resolver.get_by_name import get_by_name
from lightly_studio.resolvers.tag_resolver.get_names_by_ids import get_names_by_ids
from lightly_studio.resolvers.tag_resolver.get_or_create_sample_tag_by_name import (
    get_or_create_sample_tag_by_name,
)
from lightly_studio.resolvers.tag_resolver.get_sample_ids_by_tag_id import (
    get_sample_ids_by_tag_id,
)
from lightly_studio.resolvers.tag_resolver.get_tags_by_sample import get_tags_by_sample
from lightly_studio.resolvers.tag_resolver.remove_sample_ids_from_tag_id import (
    remove_sample_ids_from_tag_id,
)
from lightly_studio.resolvers.tag_resolver.remove_tag_from_sample import remove_tag_from_sample
from lightly_studio.resolvers.tag_resolver.rename import rename
from lightly_studio.resolvers.tag_resolver.split_samples import (
    SplitDefinition,
    split_samples,
)

__all__ = [
    "SplitDefinition",
    "add_sample_ids_to_tag_id",
    "add_samples_to_tag_from_query",
    "add_tag_to_sample",
    "create",
    "delete",
    "get_all_by_collection_id",
    "get_by_id",
    "get_by_name",
    "get_names_by_ids",
    "get_or_create_sample_tag_by_name",
    "get_sample_ids_by_tag_id",
    "get_tags_by_sample",
    "remove_sample_ids_from_tag_id",
    "remove_tag_from_sample",
    "rename",
    "split_samples",
]
