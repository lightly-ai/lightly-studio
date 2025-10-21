"""Module to launch the GUI."""

from __future__ import annotations

from lightly_studio import db_manager
from lightly_studio.api.server import Server
from lightly_studio.dataset import env
from lightly_studio.resolvers import dataset_resolver, sample_resolver


def _validate_has_samples() -> None:
    """Validate that there are samples in the database before starting GUI.

    Raises:
        ValueError: If no datasets are found or if no samples exist in any dataset.
    """
    session = db_manager.persistent_session()

    # Check if any datasets exist
    datasets = dataset_resolver.get_all(session=session, offset=0, limit=1)

    if not datasets:
        raise ValueError(
            "No datasets found. Please load a dataset using Dataset class methods "
            "(e.g., add_samples_from_path(), add_samples_from_yolo(), etc.) "
            "before starting the GUI."
        )

    # Check if there are any samples in the first dataset
    first_dataset = datasets[0]
    sample_count = sample_resolver.count_by_dataset_id(
        session=session, dataset_id=first_dataset.dataset_id
    )

    if sample_count == 0:
        raise ValueError(
            "No images have been indexed for the first dataset. "
            "Please ensure your dataset contains valid images and try loading again."
        )


def start_gui() -> None:
    """Launch the web interface for the loaded dataset."""
    _validate_has_samples()

    server = Server(host=env.LIGHTLY_STUDIO_HOST, port=env.LIGHTLY_STUDIO_PORT)

    print(f"Open the LightlyStudio GUI under: {env.APP_URL}")

    server.start()
