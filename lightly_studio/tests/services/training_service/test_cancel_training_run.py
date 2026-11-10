from __future__ import annotations

import sys
from pathlib import Path
from uuid import uuid4

import pytest
from sqlmodel import Session

from lightly_studio.errors import NotFoundError
from lightly_studio.models.training_run import TrainingRunCreate, TrainingRunStatus
from lightly_studio.services.training_service import cancel_training_run, start_training_run
from lightly_studio.services.training_service.training_run_registry import TrainingRunRegistry
from tests.services.training_service import helpers


def test_cancel_training_run(db_session: Session, tmp_path: Path) -> None:
    dataset = helpers.create_training_dataset(session=db_session)
    registry = TrainingRunRegistry()
    script_path = helpers.write_script(tmp_path=tmp_path, content="import time\ntime.sleep(30)\n")
    run = start_training_run.start_training_run(
        session=db_session,
        collection=dataset.collection,
        run_create=TrainingRunCreate(
            train_tag_id=dataset.train_tag_id,
            val_tag_id=dataset.val_tag_id,
            gt_annotation_collection_id=dataset.gt_annotation_collection_id,
        ),
        registry=registry,
        runs_dir=tmp_path / "runs",
        runner_command=[sys.executable, str(script_path)],
        session_factory=helpers.session_factory_for(session=db_session),
    )

    cancel_training_run.cancel_training_run(
        registry=registry,
        collection_id=dataset.collection.collection_id,
        training_run_id=run.training_run_id,
    )
    helpers.wait_until_done(run=run)

    assert run.status == TrainingRunStatus.CANCELLED
    with pytest.raises(ValueError, match="can be cancelled"):
        cancel_training_run.cancel_training_run(
            registry=registry,
            collection_id=dataset.collection.collection_id,
            training_run_id=run.training_run_id,
        )


def test_cancel_training_run__not_found() -> None:
    with pytest.raises(NotFoundError):
        cancel_training_run.cancel_training_run(
            registry=TrainingRunRegistry(), collection_id=uuid4(), training_run_id=uuid4()
        )
