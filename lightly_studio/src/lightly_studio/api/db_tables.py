"""Module provides functions to initialize and manage the DuckDB."""

# Import SampleTable first to avoid circular imports. Needs I001 to prevent import sorting.
from lightly_studio.models.sample import (  # noqa: I001
    SampleTable,  # noqa: F401, required for SQLModel to work properly
)
from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,  # noqa: F401, required for SQLModel to work properly
)
from lightly_studio.models.annotation_label import (
    AnnotationLabelTable,  # noqa: F401, required for SQLModel to work properly
)
from lightly_studio.models.collection import (
    CollectionTable,  # noqa: F401, required for SQLModel to work properly
)
from lightly_studio.models.embedding_model import (
    EmbeddingModelTable,  # noqa: F401, required for SQLModel to work properly
)
from lightly_studio.models.image import (
    ImageTable,  # noqa: F401, required for SQLModel to work properly
)
from lightly_studio.models.metadata import (
    SampleMetadataTable,  # noqa: F401, required for SQLModel to work properly
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
from lightly_studio.models.two_dim_embedding import (
    TwoDimEmbeddingTable,  # noqa: F401, required for SQLModel to work properly
)
