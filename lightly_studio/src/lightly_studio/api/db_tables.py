"""Module provides functions to initialize and manage the DuckDB."""

from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,  # noqa: F401, required for SQLModel to work properly
)
from lightly_studio.models.annotation_label import (
    AnnotationLabelTable,  # noqa: F401, required for SQLModel to work properly
)
from lightly_studio.models.dataset import (
    DatasetTable,  # noqa: F401, required for SQLModel to work properly
)
from lightly_studio.models.embedding_model import (
    EmbeddingModelTable,  # noqa: F401, required for SQLModel to work properly
)
from lightly_studio.models.metadata import (
    SampleMetadataTable,  # noqa: F401, required for SQLModel to work properly
)
from lightly_studio.models.sample import (
    SampleTable,  # noqa: F401, required for SQLModel to work properly
)
from lightly_studio.models.sample_embedding import (
    SampleEmbeddingTable,  # noqa: F401, required for SQLModel to work properly
)
from lightly_studio.models.settings import (
    SettingTable,  # noqa: F401, required for SQLModel to work properly
)
from lightly_studio.models.tag import (
    TagTable,  # noqa: F401, required for SQLModel to work properly
)
