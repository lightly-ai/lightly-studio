"""Tests for delete_dataset that need no database.

`test_delete_dataset.py` is `postgres_only`, so the default DuckDB run skips every test in it.
A test with a mocked session belongs here, where that run collects it.
"""

from __future__ import annotations

import uuid

from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.export import export_artifact

# The package exports the `delete_dataset` function under the module's own name, so the module
# itself is only reachable through a direct import.
from lightly_studio.resolvers.dataset_resolver.delete_dataset import _delete_export_jobs


def test_delete_export_jobs(mocker: MockerFixture) -> None:
    session = mocker.MagicMock(spec=Session)
    session.exec.return_value.all.return_value = ["/tmp/export-1/coco.json", "/tmp/export-2"]
    remove_export_artifact = mocker.patch.object(export_artifact, "remove_export_artifact")

    _delete_export_jobs(session=session, dataset_id=uuid.uuid4())

    assert remove_export_artifact.call_args_list == [
        mocker.call(export_path="/tmp/export-1/coco.json"),
        mocker.call(export_path="/tmp/export-2"),
    ]
