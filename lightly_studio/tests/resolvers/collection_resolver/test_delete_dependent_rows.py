from __future__ import annotations

from sqlmodel import Session, select

from lightly_studio.models.annotation_collection_coverage import (
    AnnotationCollectionCoverageTable,
)
from lightly_studio.models.collection import SampleType
from lightly_studio.models.collection_embedding_model import CollectionEmbeddingModelTable
from lightly_studio.models.export_job import ExportJobTable
from lightly_studio.models.tag import TagTable
from lightly_studio.resolvers import annotation_collection_coverage_resolver, collection_resolver
from tests.helpers_resolvers import (
    create_collection,
    create_embedding_model,
    create_image,
    create_tag,
)


def test_delete_dependent_rows(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    deleted, kept = (
        create_collection(
            session=db_session,
            collection_name=name,
            parent_collection_id=collection.collection_id,
            sample_type=SampleType.ANNOTATION,
        )
        for name in ("predictions", "ground_truth")
    )
    for source in (deleted, kept):
        annotation_collection_coverage_resolver.add_many(
            session=db_session,
            annotation_collection_id=source.collection_id,
            parent_sample_ids=[image.sample_id],
        )
        create_embedding_model(session=db_session, collection_id=source.collection_id)
        create_tag(session=db_session, collection_id=source.collection_id, tag_name="reviewed")
        db_session.add(
            ExportJobTable(collection_id=source.collection_id, export_path=f"/tmp/{source.name}")
        )

    collection_resolver.delete_dependent_rows(
        session=db_session, collection_id=deleted.collection_id
    )
    db_session.commit()

    coverage = db_session.exec(select(AnnotationCollectionCoverageTable)).all()
    assert [row.annotation_collection_id for row in coverage] == [kept.collection_id]
    links = db_session.exec(select(CollectionEmbeddingModelTable)).all()
    assert [link.collection_id for link in links] == [kept.collection_id]
    tags = db_session.exec(select(TagTable)).all()
    assert [tag.collection_id for tag in tags] == [kept.collection_id]
    export_jobs = db_session.exec(select(ExportJobTable)).all()
    assert [job.collection_id for job in export_jobs] == [kept.collection_id]
