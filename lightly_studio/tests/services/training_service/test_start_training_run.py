from __future__ import annotations

import sys
from pathlib import Path
from uuid import UUID

import pytest
from sqlmodel import Session

from lightly_studio.models.training_run import TrainingRunCreate, TrainingRunStatus
from lightly_studio.resolvers import annotation_resolver, evaluation_run_resolver
from lightly_studio.services.training_service import start_training_run
from lightly_studio.services.training_service.training_run_registry import (
    TrainingRun,
    TrainingRunRegistry,
)
from tests.helpers_resolvers import create_collection, create_tag
from tests.services.training_service import helpers


def test_start_training_run(db_session: Session, tmp_path: Path) -> None:
    dataset = helpers.create_training_dataset(session=db_session)
    registry = TrainingRunRegistry()

    run = _start(
        session=db_session,
        dataset=dataset,
        registry=registry,
        tmp_path=tmp_path,
        script=helpers.FAKE_RUNNER_SCRIPT,
    )
    helpers.wait_until_done(run=run)

    assert run.status == TrainingRunStatus.COMPLETED, run.error
    assert registry.list_for_collection(collection_id=dataset.collection.collection_id) == [run]
    assert run.train_sample_count == 1
    assert run.val_sample_ids == [dataset.images[1].sample_id]
    # The fake runner predicts one box on each of the 3 images.
    predictions = annotation_resolver.get_all_by_collection_name(
        session=db_session,
        collection_name=run.name,
        parent_collection_id=dataset.collection.collection_id,
    ).annotations
    assert len(predictions) == 3
    runs = evaluation_run_resolver.get_all_by_dataset_id(
        session=db_session, dataset_id=dataset.collection.dataset_id
    )
    assert [str(r.id) for r in runs] == [str(run.evaluation_run_id)]
    assert runs[0].name == run.name


def test_start_training_run__process_fails(db_session: Session, tmp_path: Path) -> None:
    dataset = helpers.create_training_dataset(session=db_session)

    run = _start(
        session=db_session,
        dataset=dataset,
        registry=TrainingRunRegistry(),
        tmp_path=tmp_path,
        script="import sys\nprint('CUDA out of memory')\nsys.exit(1)\n",
    )
    helpers.wait_until_done(run=run)

    assert run.status == TrainingRunStatus.FAILED
    assert run.error == "CUDA out of memory"
    assert run.evaluation_run_id is None


def test_start_training_run__same_tags(db_session: Session, tmp_path: Path) -> None:
    dataset = helpers.create_training_dataset(session=db_session)

    with pytest.raises(ValueError, match="must be different"):
        _start(
            session=db_session,
            dataset=dataset,
            registry=TrainingRunRegistry(),
            tmp_path=tmp_path,
            script=helpers.FAKE_RUNNER_SCRIPT,
            val_tag_id=dataset.train_tag_id,
        )


def test_start_training_run__tag_without_samples(db_session: Session, tmp_path: Path) -> None:
    dataset = helpers.create_training_dataset(session=db_session)
    empty_tag = create_tag(
        session=db_session, collection_id=dataset.collection.collection_id, tag_name="empty"
    )

    with pytest.raises(ValueError, match="Tag 'empty' has no samples"):
        _start(
            session=db_session,
            dataset=dataset,
            registry=TrainingRunRegistry(),
            tmp_path=tmp_path,
            script=helpers.FAKE_RUNNER_SCRIPT,
            val_tag_id=empty_tag.tag_id,
        )


def test_start_training_run__gt_not_an_annotation_source(
    db_session: Session, tmp_path: Path
) -> None:
    dataset = helpers.create_training_dataset(session=db_session)
    other_collection = create_collection(session=db_session)

    with pytest.raises(ValueError, match="not an annotation source of this collection"):
        _start(
            session=db_session,
            dataset=dataset,
            registry=TrainingRunRegistry(),
            tmp_path=tmp_path,
            script=helpers.FAKE_RUNNER_SCRIPT,
            gt_annotation_collection_id=other_collection.collection_id,
        )
    assert not (tmp_path / "runs").exists()


def test_start_training_run__run_already_active(db_session: Session, tmp_path: Path) -> None:
    dataset = helpers.create_training_dataset(session=db_session)
    registry = TrainingRunRegistry()
    first_run = _start(
        session=db_session,
        dataset=dataset,
        registry=registry,
        tmp_path=tmp_path,
        script="import time\ntime.sleep(30)\n",
    )

    with pytest.raises(ValueError, match="already active"):
        _start(
            session=db_session,
            dataset=dataset,
            registry=registry,
            tmp_path=tmp_path,
            script=helpers.FAKE_RUNNER_SCRIPT,
        )

    first_run.cancel_requested = True
    assert first_run.process is not None
    first_run.process.kill()
    helpers.wait_until_done(run=first_run)


def _start(  # noqa: PLR0913
    session: Session,
    dataset: helpers.TrainingDataset,
    registry: TrainingRunRegistry,
    tmp_path: Path,
    script: str,
    val_tag_id: UUID | None = None,
    gt_annotation_collection_id: UUID | None = None,
) -> TrainingRun:
    script_path = helpers.write_script(tmp_path=tmp_path, content=script)
    return start_training_run.start_training_run(
        session=session,
        collection=dataset.collection,
        run_create=TrainingRunCreate(
            train_tag_id=dataset.train_tag_id,
            val_tag_id=val_tag_id or dataset.val_tag_id,
            gt_annotation_collection_id=(
                gt_annotation_collection_id or dataset.gt_annotation_collection_id
            ),
            steps=2,
        ),
        registry=registry,
        runs_dir=tmp_path / "runs",
        runner_command=[sys.executable, str(script_path)],
        session_factory=helpers.session_factory_for(session=session),
    )
