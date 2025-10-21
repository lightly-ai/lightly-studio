from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from lightly_studio.api.routes.api import features


def test_get_features(test_client: TestClient, mocker: MockerFixture) -> None:
    """Test that the /features endpoint returns the list of active features."""
    mock_features = ["feature1", "feature2", "feature3"]

    mocker.patch.object(
        features,
        "lightly_studio_active_features",
        mock_features,
    )
    response = test_client.get("/api/features")
    assert response.status_code == 200
    assert response.json() == mock_features
