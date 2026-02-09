from __future__ import annotations

import io
from pathlib import Path
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_OK,
)
from lightly_studio.few_shot_classifier.classifier import (
    ExportType,
)
from lightly_studio.few_shot_classifier.classifier_manager import (
    ClassifierEntry,
    ClassifierManager,
    ClassifierManagerProvider,
)
from lightly_studio.few_shot_classifier.random_forest_classifier import (
    RandomForest,
)
from lightly_studio.models.classifier import EmbeddingClassifier


def test_get_negative_samples(mocker: MockerFixture, test_client: TestClient) -> None:
    """Test get_negative_samples endpoint with mocked Sample objects."""
    # Create mock sample objects that will be returned by
    # provide_negative_samples.
    mock_samples = [
        mocker.Mock(sample_id=uuid4()),
        mocker.Mock(sample_id=uuid4()),
        mocker.Mock(sample_id=uuid4()),
    ]

    # Initialize classifier_manager with a mock variant.
    mock_classifier_manager = mocker.Mock(spec_set=ClassifierManager)
    mock_classifier_manager.provide_negative_samples.return_value = mock_samples

    mocker.patch.object(
        ClassifierManagerProvider,
        "get_classifier_manager",
        return_value=mock_classifier_manager,
    )

    # Prepare request parameters.
    collection_id = uuid4()
    positive_samples = [uuid4(), uuid4()]
    params = {
        "positive_sample_ids": [str(sample_id) for sample_id in positive_samples],
        "collection_id": str(collection_id),
    }

    # Make the request.
    response = test_client.post("/api/classifiers/get_negative_samples", json=params)

    # Assert the response.
    assert response.status_code == HTTP_STATUS_OK
    response_data = response.json()
    assert sorted(response_data["negative_sample_ids"]) == sorted(
        str(s.sample_id) for s in mock_samples
    )

    # Verify the classifier manager was called correctly.
    mock_classifier_manager.provide_negative_samples.assert_called_once_with(
        session=mocker.ANY,
        collection_id=collection_id,
        selected_samples=positive_samples,
    )


def test_samples_to_refine(mocker: MockerFixture, test_client: TestClient) -> None:
    """Test the samples_to_refine endpoint."""
    # Initialize the mock classifier manager
    mock_classifier_manager = mocker.Mock(spec_set=ClassifierManager)

    # Create UUIDs for testing
    sample_uuids_1 = [uuid4(), uuid4()]
    sample_uuids_2 = [uuid4(), uuid4()]

    # Set up the return value for get_samples_for_fine_tuning
    mock_samples = {"class_1": sample_uuids_1, "class_2": sample_uuids_2}
    mock_classifier_manager.get_samples_for_fine_tuning.return_value = mock_samples

    mocker.patch.object(
        ClassifierManagerProvider,
        "get_classifier_manager",
        return_value=mock_classifier_manager,
    )

    # Make the request
    classifier_id = uuid4()
    collection_id = uuid4()
    response = test_client.get(
        f"/api/classifiers/{classifier_id}/samples_to_refine",
        params={"collection_id": str(collection_id)},
    )

    # Assert the response
    assert response.status_code == HTTP_STATUS_OK

    # Compare with string versions of UUIDs
    expected_response = {
        "samples": {
            "class_1": [str(uuid) for uuid in sample_uuids_1],
            "class_2": [str(uuid) for uuid in sample_uuids_2],
        }
    }
    assert response.json() == expected_response

    # Check that get_samples_for_fine_tuning was called with correct parameters
    mock_classifier_manager.get_samples_for_fine_tuning.assert_called_once_with(
        session=mocker.ANY,
        collection_id=collection_id,
        classifier_id=classifier_id,
    )


def test_commit_temp_classifier(mocker: MockerFixture, test_client: TestClient) -> None:
    # Initialize the classifier_manager with a mock variant so it does not
    # update the singleton.
    mock_classifier_manager = mocker.Mock(spec_set=ClassifierManager)
    mocker.patch.object(
        ClassifierManagerProvider,
        "get_classifier_manager",
        return_value=mock_classifier_manager,
    )
    mock_id = uuid4()

    # Make the request.
    response = test_client.post(f"/api/classifiers/{mock_id}/commit_temp_classifier")
    # Assert the response
    assert response.status_code == HTTP_STATUS_OK

    # Check that the commit_temp_classifier method was called
    mock_classifier_manager.commit_temp_classifier.assert_called_once_with(classifier_id=mock_id)


def test_drop_temp_classifier(mocker: MockerFixture, test_client: TestClient) -> None:
    # Initialize the classifier_manager with a mock variant so it does not
    # update the singleton.
    mock_classifier_manager = mocker.Mock(spec_set=ClassifierManager)
    mocker.patch.object(
        ClassifierManagerProvider,
        "get_classifier_manager",
        return_value=mock_classifier_manager,
    )
    mock_id = uuid4()

    # Make the request.
    response = test_client.delete(f"/api/classifiers/{mock_id}/drop_temp_classifier")
    # Assert the response
    assert response.status_code == HTTP_STATUS_OK

    # Check that the classifier manager's drop_temp_classifier method was called
    mock_classifier_manager.drop_temp_classifier.assert_called_once_with(classifier_id=mock_id)


def test_save_classifier_to_file(mocker: MockerFixture, test_client: TestClient) -> None:
    # Initialize the classifier_manager with a mock variant so it does not
    # update the singleton.
    mock_classifier_manager = mocker.Mock(spec_set=ClassifierManager)
    mocker.patch.object(
        ClassifierManagerProvider,
        "get_classifier_manager",
        return_value=mock_classifier_manager,
    )
    mock_id = uuid4()
    mock_classifier = EmbeddingClassifier(
        classifier_name="classifier1",
        class_list=["class1", "class2"],
        classifier_id=mock_id,
    )
    mock_classifier_manager.get_classifier_by_id.return_value = mock_classifier

    # Mock save_classifier_to_buffer to write some test data
    def mock_save_to_buffer(
        classifier_id: UUID, buffer: io.BytesIO, export_type: ExportType
    ) -> None:
        content = f"test binary data - {classifier_id}.{export_type}"
        bcontent = content.encode("utf-8")
        buffer.write(bcontent)

    mock_classifier_manager.save_classifier_to_buffer.side_effect = mock_save_to_buffer
    export_type = "lightly"
    # Make the request
    response = test_client.post(f"/api/classifiers/{mock_id}/save_classifier_to_file/{export_type}")

    # Assert response
    assert response.status_code == HTTP_STATUS_OK
    assert response.headers["content-type"] == "application/octet-stream"
    assert response.headers["content-disposition"] == 'attachment; filename="classifier1.pkl"'
    content = f"test binary data - {mock_id}.{export_type}"
    bcontent = content.encode("utf-8")
    assert response.content == bcontent

    # Verify the save_classifier_to_buffer was called correctly
    mock_classifier_manager.save_classifier_to_buffer.assert_called_once()
    call_args = mock_classifier_manager.save_classifier_to_buffer.call_args[1]
    assert call_args["classifier_id"] == mock_id
    assert isinstance(call_args["buffer"], io.BytesIO)


def test_load_classifier_from_file(mocker: MockerFixture, test_client: TestClient) -> None:
    # Initialize the classifier_manager with a mock variant so it does not
    # update the singleton.
    mock_classifier_manager = mocker.Mock(spec_set=ClassifierManager)
    # Set up the return value for load_classifier_from_file
    mock_id = uuid4()
    mock_collection_id = uuid4()
    mock_classifier_manager.load_classifier_from_file.return_value = ClassifierEntry(
        few_shot_classifier=RandomForest(
            name="mock_name",
            classes=["class1", "class2"],
            embedding_model_hash="mock_hash",
            embedding_model_name="mock_model",
        ),
        classifier_id=mock_id,
        is_active=True,
        annotations={},
        collection_id=mock_collection_id,
    )
    mocker.patch.object(
        ClassifierManagerProvider,
        "get_classifier_manager",
        return_value=mock_classifier_manager,
    )

    # Make the request.
    response = test_client.post(
        "/api/classifiers/load_classifier_from_file",
        json={"file_path": "path/to/file", "collection_id": str(mock_collection_id)},
    )
    # Assert the response
    assert response.status_code == HTTP_STATUS_OK

    # Check that the load_classifier_from_file method was called
    mock_classifier_manager.load_classifier_from_file.assert_called_once_with(
        session=mocker.ANY, file_path=Path("path/to/file"), collection_id=mock_collection_id
    )

    # Check that the response contains the classifier ID with the correct format
    response_json = response.json()
    assert "classifier_id" in response_json
    assert response_json["classifier_id"] == str(mock_id)


def test_train_classifier(mocker: MockerFixture, test_client: TestClient) -> None:
    # Initialize the classifier_manager with a mock variant so it does not
    # update the singleton.
    mock_classifier_manager = mocker.Mock(spec_set=ClassifierManager)
    mocker.patch.object(
        ClassifierManagerProvider,
        "get_classifier_manager",
        return_value=mock_classifier_manager,
    )
    mock_id = uuid4()

    # Make the request.
    response = test_client.post(f"/api/classifiers/{mock_id}/train_classifier")
    # Assert the response
    assert response.status_code == HTTP_STATUS_OK

    # Check that the train_classifier method was called
    mock_classifier_manager.train_classifier.assert_called_once_with(
        session=mocker.ANY, classifier_id=mock_id
    )


def test_create_classifier(mocker: MockerFixture, test_client: TestClient) -> None:
    # Initialize the classifier_manager with a mock variant so it does not
    # update the singleton.
    mock_classifier_manager = mocker.Mock(spec_set=ClassifierManager)
    mock_id = uuid4()
    mock_name = "test_classifier"

    mock_classifier_manager.create_classifier.return_value = ClassifierEntry(
        few_shot_classifier=RandomForest(
            name=mock_name,
            classes=["class1", "class2"],
            embedding_model_hash="mock_hash",
            embedding_model_name="mock_model",
        ),
        classifier_id=mock_id,
        is_active=True,
        annotations={},
        collection_id=uuid4(),
    )

    mocker.patch.object(
        ClassifierManagerProvider,
        "get_classifier_manager",
        return_value=mock_classifier_manager,
    )

    # Make the request.
    collection_id = uuid4()
    request_data = {
        "name": mock_name,
        "class_list": ["class1", "class2"],
        "collection_id": str(collection_id),
    }
    response = test_client.post("/api/classifiers/create", json=request_data)

    # Assert the response.
    assert response.status_code == HTTP_STATUS_OK
    response_json = response.json()
    assert response_json == {
        "name": mock_name,
        "classifier_id": str(mock_id),
    }

    # Check that create_classifier was called with correct parameters.
    mock_classifier_manager.create_classifier.assert_called_once_with(
        session=mocker.ANY,
        name=request_data["name"],
        class_list=request_data["class_list"],
        collection_id=collection_id,
    )


def test_update_annotations(mocker: MockerFixture, test_client: TestClient) -> None:
    """Test the update_annotations endpoint."""
    # Initialize the classifier_manager with a mock variant so it does not
    # update the singleton.
    mock_classifier_manager = mocker.Mock(spec_set=ClassifierManager)
    mocker.patch.object(
        ClassifierManagerProvider,
        "get_classifier_manager",
        return_value=mock_classifier_manager,
    )
    mock_id = uuid4()
    mock_annotations = {
        "class1": [uuid4(), uuid4()],
        "class2": [uuid4()],
    }

    # Make the request.
    response = test_client.post(
        f"/api/classifiers/{mock_id}/update_annotations",
        json={
            "annotations": {
                key: [str(sample_id) for sample_id in value]
                for key, value in mock_annotations.items()
            }
        },
    )
    # Assert the response.
    assert response.status_code == HTTP_STATUS_OK
    # Check that update_annotations was called with correct parameters.
    mock_classifier_manager.update_classifiers_annotations.assert_called_once_with(
        classifier_id=mock_id,
        new_annotations=mock_annotations,
    )


def test_get_all_classifiers(mocker: MockerFixture, test_client: TestClient) -> None:
    """Test the get_all_classifiers endpoint."""
    # Initialize the mock classifier manager.
    mock_classifier_manager = mocker.Mock(spec_set=ClassifierManager)

    # Create test data with EmbeddingClassifier objects.
    classifier_id1 = uuid4()
    classifier_id2 = uuid4()
    collection_id = uuid4()
    mock_classifiers = [
        EmbeddingClassifier(
            classifier_name="classifier1",
            classifier_id=classifier_id1,
            class_list=["class1", "class2"],
        ),
        EmbeddingClassifier(
            classifier_name="classifier2",
            classifier_id=classifier_id2,
            class_list=["class3"],
        ),
    ]
    mock_classifier_manager.get_all_classifiers.return_value = mock_classifiers

    mocker.patch.object(
        ClassifierManagerProvider,
        "get_classifier_manager",
        return_value=mock_classifier_manager,
    )

    # Make the request.
    response = test_client.get(
        "/api/classifiers/get_all_classifiers",
        params={"collection_id": str(collection_id)},
    )

    # Assert the response.
    assert response.status_code == HTTP_STATUS_OK
    response_json = response.json()
    assert "classifiers" in response_json

    # Check that the response matches our test data.
    expected_classifiers = [
        {
            "classifier_name": "classifier1",
            "classifier_id": str(classifier_id1),
            "class_list": ["class1", "class2"],
        },
        {
            "classifier_name": "classifier2",
            "classifier_id": str(classifier_id2),
            "class_list": ["class3"],
        },
    ]
    assert response_json["classifiers"] == expected_classifiers

    # Check that get_all_classifiers was called with collection_id.
    mock_classifier_manager.get_all_classifiers.assert_called_once_with(
        collection_id=collection_id,
    )


def test_load_classifier_from_buffer(mocker: MockerFixture, test_client: TestClient) -> None:
    """Test the load_classifier_from_buffer endpoint."""
    # Initialize the mock classifier manager
    mock_classifier_manager = mocker.Mock(spec_set=ClassifierManager)
    mock_id = uuid4()

    mock_collection_id = uuid4()
    mock_classifier_manager.load_classifier_from_buffer.return_value = ClassifierEntry(
        few_shot_classifier=RandomForest(
            name="mock_name",
            classes=["class1", "class2"],
            embedding_model_hash="mock_hash",
            embedding_model_name="mock_model",
        ),
        classifier_id=mock_id,
        collection_id=mock_collection_id,
        is_active=True,
        annotations={},
    )
    mocker.patch.object(
        ClassifierManagerProvider,
        "get_classifier_manager",
        return_value=mock_classifier_manager,
    )

    # Create a mock file with some test content
    test_content = b"test classifier data"
    mock_file = mocker.Mock()
    mock_file.file.read.return_value = test_content

    # Make the request
    response = test_client.post(
        "/api/classifiers/load_classifier_from_buffer",
        params={"collection_id": str(mock_collection_id)},
        files={
            "file": (
                "test_classifier.pkl",
                io.BytesIO(test_content),
                "application/octet-stream",
            )
        },
    )

    # Assert the response
    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == str(mock_id)

    # Verify the classifier manager was called correctly
    mock_classifier_manager.load_classifier_from_buffer.assert_called_once()
    call_args = mock_classifier_manager.load_classifier_from_buffer.call_args[1]
    assert call_args["session"] is not None
    assert call_args["collection_id"] == mock_collection_id
    assert call_args["buffer"].getvalue() == test_content


def test_run_classifier_with_success(mocker: MockerFixture, test_client: TestClient) -> None:
    """Test the run_classifier_route endpoint."""
    # Initialize the classifier_manager with a mock variant
    mock_classifier_manager = mocker.Mock(spec_set=ClassifierManager)
    mocker.patch.object(
        ClassifierManagerProvider,
        "get_classifier_manager",
        return_value=mock_classifier_manager,
    )

    # Create test UUIDs
    collection_id = uuid4()
    classifier_id = uuid4()

    response = test_client.post(
        f"/api/classifiers/{classifier_id}/run_on_collection/{collection_id}"
    )

    # Assert the response
    assert response.status_code == HTTP_STATUS_OK

    # Verify run_classifier was called with correct arguments
    mock_classifier_manager.run_classifier.assert_called_once_with(
        session=mocker.ANY,
        classifier_id=classifier_id,
        collection_id=collection_id,
    )


def test_sample_history(mocker: MockerFixture, test_client: TestClient) -> None:
    """Test the sample_history endpoint."""
    # Initialize the mock classifier manager
    mock_classifier_manager = mocker.Mock(spec_set=ClassifierManager)

    # Create UUIDs for testing
    sample_uuids_1 = [uuid4(), uuid4()]
    sample_uuids_2 = [uuid4(), uuid4()]

    # Set up the return value for get_annotations
    mock_samples = {"class_1": sample_uuids_1, "class_2": sample_uuids_2}
    mock_classifier_manager.get_annotations.return_value = mock_samples

    mocker.patch.object(
        ClassifierManagerProvider,
        "get_classifier_manager",
        return_value=mock_classifier_manager,
    )

    # Make the request
    classifier_id = uuid4()
    response = test_client.get(
        f"/api/classifiers/{classifier_id}/sample_history",
    )

    # Assert the response
    assert response.status_code == HTTP_STATUS_OK

    # Compare with string versions of UUIDs
    expected_response = {
        "samples": {
            "class_1": [str(uuid) for uuid in sample_uuids_1],
            "class_2": [str(uuid) for uuid in sample_uuids_2],
        }
    }
    assert response.json() == expected_response

    # Check that get_samples_for_fine_tuning was called with correct parameters
    mock_classifier_manager.get_annotations.assert_called_once_with(classifier_id=classifier_id)
