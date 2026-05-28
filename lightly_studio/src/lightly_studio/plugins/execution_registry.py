"""In-memory registry of operator executions.

Operator executions are dispatched to a background thread pool. Each submission
returns immediately with an ``ExecutionRecord``; the GUI polls the registry to
follow progress.

State is kept in-process only and is lost on server restart.
"""

from __future__ import annotations

import logging
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from collections.abc import Generator
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Optional
from uuid import UUID

from sqlmodel import Session

from lightly_studio import db_manager
from lightly_studio.plugins.base_operator import BaseOperator, OperatorResult, OperatorStatus
from lightly_studio.plugins.operator_context import ExecutionContext

logger = logging.getLogger(__name__)

# Factory that yields a short-lived DB session for the worker thread.
SessionFactory = Callable[[], AbstractContextManager[Session]]


@contextmanager
def worker_session() -> Generator[Session, None, None]:
    """Open a fresh DB session for a background worker.

    Bypasses ``db_manager.session()`` on purpose: that context manager commits the
    *global* persistent session on enter/exit, which races with the request thread
    when two threads touch it simultaneously. The worker owns its own session and
    leaves the persistent session alone.
    """
    engine = db_manager.get_engine()._engine  # noqa: SLF001 — see module docstring
    session = Session(engine, close_resets_only=False)
    try:
        yield session
        if session.in_transaction():
            session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@dataclass
class ExecutionRecord:
    """Per-execution state surfaced to the GUI."""

    execution_id: UUID
    operator_id: str
    operator_name: str
    status: OperatorStatus
    started_at: datetime
    finished_at: Optional[datetime] = None
    result: Optional[OperatorResult] = None
    error_message: Optional[str] = None


@dataclass
class _RegistryState:
    records: dict[UUID, ExecutionRecord] = field(default_factory=dict)


class ExecutionRegistry:
    """Tracks the lifecycle of operator executions across background threads."""

    def __init__(self, max_workers: int = 4) -> None:
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="op-exec"
        )
        self._state = _RegistryState()
        self._lock = threading.Lock()

    def submit(
        self,
        *,
        operator: BaseOperator,
        operator_id: str,
        session_factory: SessionFactory,
        context: ExecutionContext,
        parameters: dict[str, Any],
    ) -> ExecutionRecord:
        """Submit an execution; returns the freshly-created RUNNING record."""
        record = ExecutionRecord(
            execution_id=uuid.uuid4(),
            operator_id=operator_id,
            operator_name=operator.name,
            status=OperatorStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
        )
        with self._lock:
            self._state.records[record.execution_id] = record
        self._executor.submit(
            self._run, record.execution_id, operator, session_factory, context, parameters
        )
        return record

    def _run(
        self,
        execution_id: UUID,
        operator: BaseOperator,
        session_factory: SessionFactory,
        context: ExecutionContext,
        parameters: dict[str, Any],
    ) -> None:
        try:
            with session_factory() as session:
                result = operator.execute(
                    session=session, context=context, parameters=parameters
                )
            # Use ERROR for soft failures (success=False) so the GUI can color them red.
            status = OperatorStatus.READY if result.success else OperatorStatus.ERROR
            self._mark_done(execution_id, status=status, result=result)
        except Exception as exc:  # noqa: BLE001 — top-level worker, log and surface
            logger.exception("Operator execution %s failed", execution_id)
            self._mark_done(
                execution_id,
                status=OperatorStatus.ERROR,
                error_message=str(exc) or exc.__class__.__name__,
            )

    def _mark_done(
        self,
        execution_id: UUID,
        *,
        status: OperatorStatus,
        result: Optional[OperatorResult] = None,
        error_message: Optional[str] = None,
    ) -> None:
        with self._lock:
            record = self._state.records.get(execution_id)
            if record is None:
                return
            record.status = status
            record.finished_at = datetime.now(timezone.utc)
            record.result = result
            record.error_message = error_message

    def get(self, execution_id: UUID) -> Optional[ExecutionRecord]:
        with self._lock:
            return self._state.records.get(execution_id)

    def list_all(self) -> list[ExecutionRecord]:
        with self._lock:
            return list(self._state.records.values())

    def remove(self, execution_id: UUID) -> Optional[ExecutionRecord]:
        with self._lock:
            return self._state.records.pop(execution_id, None)

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False)


execution_registry = ExecutionRegistry()
