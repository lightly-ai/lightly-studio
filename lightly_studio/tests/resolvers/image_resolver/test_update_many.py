from uuid import uuid4

from sqlmodel import Session

from lightly_studio.models.dataset import DatasetTable
from lightly_studio.resolvers import image_resolver
from tests.helpers_resolvers import (
    create_image,
)


def test_update_many_updates_dimensions_and_status(
    db_session: Session, dataset: DatasetTable
) -> None:
    image_a = create_image(session=db_session, dataset_id=dataset.dataset_id, width=10, height=20)
    image_b = create_image(session=db_session, dataset_id=dataset.dataset_id, width=30, height=40)

    updates = [
        image_resolver.ImageUpdate(
            sample_id=image_a.sample_id,
            width=100,
            height=200,
            status_metadata="ready",
        ),
        image_resolver.ImageUpdate(
            sample_id=image_b.sample_id,
            width=300,
            height=400,
            status_metadata="queued",
            status_embeddings="failed",
        ),
        # Should be ignored because it does not exist.
        image_resolver.ImageUpdate(sample_id=uuid4(), width=500, height=600),
    ]

    updated_rows = image_resolver.update_many(session=db_session, updates=updates)
    assert updated_rows == 2

    updated_a = image_resolver.get_by_id(session=db_session, sample_id=image_a.sample_id)
    updated_b = image_resolver.get_by_id(session=db_session, sample_id=image_b.sample_id)
    assert updated_a is not None
    assert updated_b is not None

    assert (updated_a.width, updated_a.height) == (100, 200)
    assert updated_a.status_metadata == "ready"
    # status_embeddings unchanged because it was not provided.
    assert updated_a.status_embeddings == "ready"

    assert (updated_b.width, updated_b.height) == (300, 400)
    assert updated_b.status_metadata == "queued"
    assert updated_b.status_embeddings == "failed"
