from collections.abc import Mapping
from typing import Any
from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.metadata import SampleMetadataTable

def bulk_update_metadata(
    session: Session,
    sample_metadata: list[tuple[UUID, Mapping[str, Any]]],
) -> None: ...
def get_by_sample_id(
    session: Session,
    sample_id: UUID,
) -> SampleMetadataTable | None: ...
def get_value_for_sample(
    session: Session,
    sample_id: UUID,
    key: str,
) -> Any | None: ...
def set_value_for_sample(
    session: Session,
    sample_id: UUID,
    key: str,
    value: Any,
) -> SampleMetadataTable: ...
