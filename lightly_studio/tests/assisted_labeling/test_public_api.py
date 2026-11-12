from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from lightly_studio_serve import server
from lightly_studio_serve.labeling_model import LabelingModel
from pytest_mock import MockerFixture

import lightly_studio as ls
from lightly_studio.assisted_labeling import labeling_model_registry
from lightly_studio.assisted_labeling.labeling_model_registry import LabelingModelRegistry
from lightly_studio.assisted_labeling.remote_labeling_model_runner import RemoteLabelingModelError
from lightly_studio.core.image.image_dataset import ImageDataset
from lightly_studio.embed.remote import connection
from lightly_studio.resolvers import labeling_model_resolver
from tests.assisted_labeling.helpers import StubLabelingModel

URL = "https://labeling.test"


def test_register_labeling_model(mocker: MockerFixture) -> None:
    registry = LabelingModelRegistry()
    mocker.patch.object(labeling_model_registry, "_registry", registry)
    model = StubLabelingModel(model_id="m")

    ls.register_labeling_model(model=model)

    assert registry.list_models() == [model]


@pytest.mark.usefixtures("patch_collection")
def test_register_remote_labeling_model(mocker: MockerFixture) -> None:
    dataset = ImageDataset.create(name="test_dataset")
    _serve(mocker=mocker, model=StubLabelingModel(model_id="car-detector"), api_key="secret")

    ls.register_remote_labeling_model(dataset=dataset, url=URL, api_key="secret")

    (saved,) = labeling_model_resolver.get_all_by_dataset_id(
        session=dataset.session, dataset_id=dataset.dataset_id
    )
    assert (saved.model_id, saved.url, saved.api_key) == ("car-detector", URL, "secret")


@pytest.mark.usefixtures("patch_collection")
def test_register_remote_labeling_model__again_updates(mocker: MockerFixture) -> None:
    dataset = ImageDataset.create(name="test_dataset")
    _serve(mocker=mocker, model=StubLabelingModel(model_id="car-detector"), api_key=None)

    ls.register_remote_labeling_model(dataset=dataset, url=URL)
    ls.register_remote_labeling_model(dataset=dataset, url="https://other.test")

    saved = labeling_model_resolver.get_all_by_dataset_id(
        session=dataset.session, dataset_id=dataset.dataset_id
    )
    assert [(model.model_id, model.url) for model in saved] == [
        ("car-detector", "https://other.test")
    ]


@pytest.mark.usefixtures("patch_collection")
def test_register_remote_labeling_model__wrong_api_key(mocker: MockerFixture) -> None:
    dataset = ImageDataset.create(name="test_dataset")
    _serve(mocker=mocker, model=StubLabelingModel(model_id="car-detector"), api_key="secret")

    with pytest.raises(RemoteLabelingModelError, match="rejects the API key"):
        ls.register_remote_labeling_model(dataset=dataset, url=URL, api_key="wrong")

    assert (
        labeling_model_resolver.get_all_by_dataset_id(
            session=dataset.session, dataset_id=dataset.dataset_id
        )
        == []
    )


def _serve(mocker: MockerFixture, model: LabelingModel, api_key: str | None) -> None:
    """Serve ``model`` to every client that ``connection.build_client`` opens."""
    mocker.patch.object(
        connection,
        "build_client",
        side_effect=lambda url: TestClient(
            server.create_app(labeling_model=model, api_key=api_key),
            base_url=url,
            follow_redirects=False,
        ),
    )
