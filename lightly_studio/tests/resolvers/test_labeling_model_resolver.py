from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.labeling_model import LabelingModelCreate
from lightly_studio.resolvers import labeling_model_resolver
from tests.helpers_resolvers import create_collection


def test_set_remote(db_session: Session) -> None:
    collection = create_collection(session=db_session)

    saved = labeling_model_resolver.set_remote(
        session=db_session,
        labeling_model=LabelingModelCreate(
            dataset_id=collection.dataset_id,
            model_id="car-detector",
            url="http://labeling.test",
            api_key="secret",
        ),
    )

    stored = labeling_model_resolver.get_by_model_id(
        session=db_session, dataset_id=collection.dataset_id, model_id="car-detector"
    )
    assert stored is not None
    assert stored.labeling_model_id == saved.labeling_model_id
    assert stored.url == "http://labeling.test"
    assert stored.api_key == "secret"
    assert "secret" not in repr(stored)


def test_set_remote__same_model_id_updates(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    first = labeling_model_resolver.set_remote(
        session=db_session,
        labeling_model=LabelingModelCreate(
            dataset_id=collection.dataset_id,
            model_id="car-detector",
            url="http://old.test",
            api_key="old",
        ),
    )

    second = labeling_model_resolver.set_remote(
        session=db_session,
        labeling_model=LabelingModelCreate(
            dataset_id=collection.dataset_id,
            model_id="car-detector",
            url="http://new.test",
            api_key=None,
        ),
    )

    assert second.labeling_model_id == first.labeling_model_id
    stored = labeling_model_resolver.get_all_by_dataset_id(
        session=db_session, dataset_id=collection.dataset_id
    )
    assert [(model.url, model.api_key) for model in stored] == [("http://new.test", None)]


def test_get_by_model_id__unknown(db_session: Session) -> None:
    collection = create_collection(session=db_session)

    assert (
        labeling_model_resolver.get_by_model_id(
            session=db_session, dataset_id=collection.dataset_id, model_id="car-detector"
        )
        is None
    )


def test_get_all_by_dataset_id(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    other_collection = create_collection(session=db_session, collection_name="other")
    for dataset_id, model_id in [
        (collection.dataset_id, "b"),
        (collection.dataset_id, "a"),
        (other_collection.dataset_id, "c"),
    ]:
        labeling_model_resolver.set_remote(
            session=db_session,
            labeling_model=LabelingModelCreate(
                dataset_id=dataset_id, model_id=model_id, url="http://labeling.test"
            ),
        )

    stored = labeling_model_resolver.get_all_by_dataset_id(
        session=db_session, dataset_id=collection.dataset_id
    )

    assert [model.model_id for model in stored] == ["a", "b"]
