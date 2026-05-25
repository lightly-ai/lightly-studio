"""Shallow image-only subset copy.

Creates a new dataset that contains only the selected image samples (``SampleTable``
plus their ``ImageTable`` rows). Unlike :func:`deep_copy_subset`, nothing else is
copied — no annotations, captions, tags, labels, embeddings, metadata, evaluation
runs, or object tracks.
"""

from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID, uuid4

from sqlmodel import Session, col, select

from lightly_studio.models.collection import (
    CollectionCreate,
    CollectionTable,
    SampleType,
)
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers import collection_resolver, dataset_resolver


def copy_images_subset(
    session: Session,
    dataset_id: UUID,
    copy_name: str,
    sample_ids: Iterable[UUID],
) -> CollectionTable:
    """Create a new image dataset containing only the given image samples.

    Args:
        session: Database session.
        dataset_id: Source dataset ID.
        copy_name: Name for the new dataset's root collection.
        sample_ids: Image sample IDs to copy. Non-image samples and IDs that do not
            belong to the source dataset are silently ignored.

    Returns:
        The new root collection.

    Raises:
        ValueError: If the source dataset does not exist or its root collection is
            not of sample type ``IMAGE``.
    """
    source_root = dataset_resolver.get_root_collection(session=session, dataset_id=dataset_id)
    if source_root.sample_type != SampleType.IMAGE:
        raise ValueError(
            f"copy_images_subset only supports IMAGE datasets, got "
            f"{source_root.sample_type.value}."
        )

    sample_id_set = set(sample_ids)

    # Resolve which of the provided IDs correspond to image samples in this dataset.
    if sample_id_set:
        valid_ids = list(
            session.exec(
                select(ImageTable.sample_id)
                .join(SampleTable, col(SampleTable.sample_id) == col(ImageTable.sample_id))
                .where(
                    col(SampleTable.collection_id) == source_root.collection_id,
                    col(ImageTable.sample_id).in_(sample_id_set),
                )
            ).all()
        )
    else:
        valid_ids = []

    # Create the new dataset (collection_resolver.create handles dataset creation
    # for root collections automatically).
    new_root = collection_resolver.create(
        session=session,
        collection=CollectionCreate(name=copy_name, sample_type=SampleType.IMAGE),
    )

    # Copy SampleTable + ImageTable rows. Nothing else.
    if valid_ids:
        old_images = session.exec(
            select(ImageTable).where(col(ImageTable.sample_id).in_(valid_ids))
        ).all()
        for old_image in old_images:
            new_sample_id = uuid4()
            session.add(
                SampleTable(sample_id=new_sample_id, collection_id=new_root.collection_id)
            )
            new_image_data = old_image.model_dump(exclude={"created_at", "updated_at"})
            new_image_data["sample_id"] = new_sample_id
            session.add(ImageTable(**new_image_data))

    session.commit()
    session.refresh(new_root)
    return new_root
