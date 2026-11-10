"""Wait for the training process of a run and handle its result."""

from __future__ import annotations

import logging
from collections.abc import Callable
from contextlib import AbstractContextManager

from sqlmodel import Session

from lightly_studio.models.training_run import TrainingRunStatus
from lightly_studio.services.training_service import finish_training_run
from lightly_studio.services.training_service.training_run_registry import TrainingRun

SessionFactory = Callable[[], AbstractContextManager[Session]]

_ERROR_LOG_LINE_COUNT = 20
logger = logging.getLogger(__name__)


def watch_training_run(run: TrainingRun, session_factory: SessionFactory) -> None:
    """Wait for the training process, then add its results or record the failure.

    Runs in a separate thread. It opens its own database session, because the session
    of the request that started the run is closed.
    """
    assert run.process is not None
    return_code = run.process.wait()
    if run.cancel_requested:
        run.status = TrainingRunStatus.CANCELLED
        return
    if return_code != 0:
        run.error = _log_tail(run=run)
        run.status = TrainingRunStatus.FAILED
        return
    try:
        with session_factory() as session:
            finish_training_run.finish_training_run(session=session, run=run)
    except Exception as error:
        logger.exception("Could not add the results of training run '%s'.", run.name)
        run.error = str(error)
        run.status = TrainingRunStatus.FAILED
        return
    run.status = TrainingRunStatus.COMPLETED


def _log_tail(run: TrainingRun) -> str:
    log_file = run.files.process_log_file
    if not log_file.exists():
        return "The training process failed."
    lines = log_file.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(lines[-_ERROR_LOG_LINE_COUNT:])
