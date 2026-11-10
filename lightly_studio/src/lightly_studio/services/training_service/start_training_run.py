"""Start a training run in a separate process."""

from __future__ import annotations

import shutil
import subprocess
import sys
import threading
from collections.abc import Sequence
from datetime import datetime, timezone
from importlib import util
from pathlib import Path
from uuid import UUID, uuid4

from sqlmodel import Session

from lightly_studio.database import db_manager
from lightly_studio.dataset import env
from lightly_studio.models.collection import CollectionTable, SampleType
from lightly_studio.models.training_run import TrainingRunCreate
from lightly_studio.resolvers import collection_resolver, tag_resolver
from lightly_studio.services.training_service import watch_training_run, write_training_files
from lightly_studio.services.training_service.training_run_files import TrainingRunFiles
from lightly_studio.services.training_service.training_run_registry import (
    TrainingRun,
    TrainingRunRegistry,
)

# The runner is started as a script, so that the training process does not import
# lightly_studio and its database setup. The spec gives its path without importing it.
_RUNNER_SPEC = util.find_spec("lightly_studio.training.training_runner")
assert _RUNNER_SPEC is not None
assert _RUNNER_SPEC.origin is not None
DEFAULT_RUNNER_COMMAND = (env.LIGHTLY_STUDIO_TRAINING_PYTHON or sys.executable, _RUNNER_SPEC.origin)


def start_training_run(  # noqa: PLR0913
    session: Session,
    collection: CollectionTable,
    run_create: TrainingRunCreate,
    registry: TrainingRunRegistry,
    runs_dir: Path,
    runner_command: Sequence[str] = DEFAULT_RUNNER_COMMAND,
    session_factory: watch_training_run.SessionFactory = db_manager.session,
) -> TrainingRun:
    """Write the training files, start the training process and a thread that waits for it.

    Raises:
        ValueError: If the inputs are not valid or a different run is active.
    """
    if registry.has_active_run():
        raise ValueError("A training run is already active. Wait for it or cancel it.")
    train_sample_ids, val_sample_ids = _split_sample_ids(
        session=session, collection=collection, run_create=run_create
    )
    created_at = datetime.now(timezone.utc)
    training_run_id = uuid4()
    run = TrainingRun(
        training_run_id=training_run_id,
        collection_id=collection.collection_id,
        name=f"lightly_train_{created_at:%Y-%m-%d_%H-%M-%S}",
        model_name=run_create.model_name,
        steps=run_create.steps,
        files=TrainingRunFiles(run_dir=runs_dir.resolve() / str(training_run_id)),
        gt_annotation_source=_gt_annotation_source_name(
            session=session, collection=collection, run_create=run_create
        ),
        val_sample_ids=val_sample_ids,
        train_sample_count=len(train_sample_ids),
        created_at=created_at,
    )
    try:
        write_training_files.write_training_files(
            session=session,
            collection=collection,
            files=run.files,
            train_sample_ids=train_sample_ids,
            val_sample_ids=val_sample_ids,
            gt_annotation_collection_id=run_create.gt_annotation_collection_id,
            model_name=run.model_name,
            steps=run.steps,
        )
    except Exception:
        shutil.rmtree(run.files.run_dir, ignore_errors=True)
        raise
    _start_process(run=run, runner_command=runner_command)
    registry.add(run)
    threading.Thread(
        target=watch_training_run.watch_training_run,
        kwargs={"run": run, "session_factory": session_factory},
        daemon=True,
    ).start()
    return run


def _split_sample_ids(
    session: Session, collection: CollectionTable, run_create: TrainingRunCreate
) -> tuple[list[UUID], list[UUID]]:
    if run_create.train_tag_id == run_create.val_tag_id:
        raise ValueError("The train tag and the val tag must be different.")
    return (
        _tag_sample_ids(session=session, collection=collection, tag_id=run_create.train_tag_id),
        _tag_sample_ids(session=session, collection=collection, tag_id=run_create.val_tag_id),
    )


def _tag_sample_ids(session: Session, collection: CollectionTable, tag_id: UUID) -> list[UUID]:
    tag = tag_resolver.get_by_id(session=session, tag_id=tag_id)
    if tag is None or tag.collection_id != collection.collection_id:
        raise ValueError(f"Tag {tag_id} is not a tag of this collection.")
    sample_ids = tag_resolver.get_sample_ids_by_tag_id(session=session, tag_id=tag_id)
    if not sample_ids:
        raise ValueError(f"Tag '{tag.name}' has no samples.")
    return sample_ids


def _gt_annotation_source_name(
    session: Session, collection: CollectionTable, run_create: TrainingRunCreate
) -> str:
    source = collection_resolver.get_by_id(
        session=session, collection_id=run_create.gt_annotation_collection_id
    )
    if (
        source is None
        or source.sample_type != SampleType.ANNOTATION
        or source.parent_collection_id != collection.collection_id
    ):
        raise ValueError("The ground truth is not an annotation source of this collection.")
    return source.name


def _start_process(run: TrainingRun, runner_command: Sequence[str]) -> None:
    with run.files.process_log_file.open("wb") as log_file:
        # The child process keeps its own handle of the log file.
        run.process = subprocess.Popen(
            [*runner_command, str(run.files.config_file)],
            stdout=log_file,
            stderr=subprocess.STDOUT,
        )
