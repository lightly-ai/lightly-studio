from __future__ import annotations

from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.api.routes.api.status import HTTP_STATUS_OK
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import collection_resolver
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_embedding_model,
    create_image,
    create_sample_embedding,
)


def test_read_annotation_embedding_coverage(db_session: Session, test_client: TestClient) -> None:
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    label = create_annotation_label(session=db_session, root_collection_id=collection.collection_id)
    annotations = [
        create_annotation(
            session=db_session,
            collection_id=collection.collection_id,
            sample_id=image.sample_id,
            annotation_label_id=label.annotation_label_id,
        )
        for _ in range(3)
    ]
    annotation_collection_id = collection_resolver.get_or_create_child_collection(
        session=db_session,
        collection_id=collection.collection_id,
        sample_type=SampleType.ANNOTATION,
    )
    model = create_embedding_model(
        session=db_session, collection_id=annotation_collection_id, embedding_dimension=2
    )
    create_sample_embedding(
        session=db_session,
        sample_id=annotations[0].sample_id,
        embedding_model_id=model.embedding_model_id,
        embedding=[1.0, 0.0],
    )

    response = test_client.post(
        f"/api/collections/{annotation_collection_id}/annotations/embedding_coverage",
        json={"filters": {"filter_type": "annotations"}},
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {"embedded_count": 1, "total_count": 3}
