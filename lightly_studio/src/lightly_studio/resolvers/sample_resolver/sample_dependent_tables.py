"""Tables with rows that reference a sample by its ``sample_id``."""

from __future__ import annotations

from lightly_studio.models.caption import CaptionTable
from lightly_studio.models.metadata import SampleMetadataTable
from lightly_studio.models.sample import SampleTagLinkTable
from lightly_studio.models.sample_embedding import SampleEmbeddingTable
from lightly_studio.models.temporal_span import TemporalSpanTable

# Delete the rows of these tables before the delete of their samples. Add a new table that
# references a sample here, so that all sample deletes remove its rows.
SAMPLE_DEPENDENT_TABLES = (
    SampleTagLinkTable,
    SampleEmbeddingTable,
    SampleMetadataTable,
    TemporalSpanTable,
    CaptionTable,
)
