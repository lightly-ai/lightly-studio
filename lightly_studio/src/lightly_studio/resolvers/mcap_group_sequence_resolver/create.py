"""Implementation of create for MCAP group sequences."""

from __future__ import annotations

from urllib import parse
from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.models.mcap_group_sequence import McapGroupSequenceTable
from lightly_studio.models.sample import SampleCreate
from lightly_studio.models.sequence import SequenceTable
from lightly_studio.resolvers import collection_resolver, sample_resolver


def create(session: Session, collection_id: UUID, mcap_path: str) -> UUID:
    """Create a sequence sample with an MCAP path in a single commit.

    Args:
        session: The database session.
        collection_id: The ID of the sequence collection.
        mcap_path: Path or URI of the MCAP file. Must be non-empty after stripping and
            its path component must end with ``.mcap``. A URI query string, for example a
            presigned URL, is ignored by the extension check.

    Returns:
        The sample ID of the created sequence.

    Raises:
        ValueError: If ``mcap_path`` is empty or its path component does not end with
            ``.mcap``, or if the collection does not exist or is not of type SEQUENCE.
    """
    path = _validated_mcap_path(mcap_path)
    collection_resolver.check_collection_type(
        session=session,
        collection_id=collection_id,
        expected_type=SampleType.SEQUENCE,
    )
    sample_id = sample_resolver.create_many(
        session=session,
        samples=[SampleCreate(collection_id=collection_id)],
    )[0]
    session.bulk_save_objects(objects=[SequenceTable(sample_id=sample_id)])
    session.bulk_save_objects(objects=[McapGroupSequenceTable(sample_id=sample_id, mcap_path=path)])
    session.commit()
    return sample_id


def _validated_mcap_path(mcap_path: str) -> str:
    path = mcap_path.strip()
    if not path:
        raise ValueError("mcap_path must be non-empty.")
    # Strip a potential URI query string, for example a presigned URL signature, so that
    # only the path component is checked for the extension.
    if not parse.urlsplit(path).path.lower().endswith(".mcap"):
        raise ValueError(f"mcap_path must end with '.mcap', got '{path}'.")
    return path
