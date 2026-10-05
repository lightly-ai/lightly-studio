"""Query for image samples lacking an embedding."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.sample_embedding import SampleEmbeddingTable


def get_unembedded_sample_ids(
    session: Session,
    collection_id: UUID,
    embedding_model_id: UUID,
) -> list[UUID]:
    """Return IDs of image samples in the collection that have no embedding of the model.

    Args:
        session: Database session for resolver operations.
        collection_id: The image collection to scan.
        embedding_model_id: Model whose existing embeddings mark an image as done.

    Returns:
        Image sample IDs that still need an embedding, ordered by image path.
    """
    embedded_ids_subquery = select(col(SampleEmbeddingTable.sample_id)).where(
        col(SampleEmbeddingTable.embedding_model_id) == embedding_model_id
    )
    sample_ids = session.exec(
        select(col(ImageTable.sample_id))
        .join(SampleTable, col(SampleTable.sample_id) == col(ImageTable.sample_id))
        .where(col(SampleTable.collection_id) == collection_id)
        .where(col(ImageTable.sample_id).notin_(embedded_ids_subquery))
        .order_by(col(ImageTable.file_path_abs))
    ).all()
    return list(sample_ids)
