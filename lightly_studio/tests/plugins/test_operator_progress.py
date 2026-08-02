from __future__ import annotations

from uuid import uuid4

from lightly_studio.plugins.operator_progress import OperatorProgress, ProgressStore


class TestProgressStore:
    def test_get__unknown_run(self) -> None:
        store = ProgressStore()

        assert store.get(run_id=uuid4()) is None

    def test_set(self) -> None:
        store = ProgressStore()
        run_id = uuid4()

        store.set(
            run_id=run_id,
            progress=OperatorProgress(current=3, total=10, description="Running inference"),
        )

        assert store.get(run_id=run_id) == OperatorProgress(
            current=3, total=10, description="Running inference"
        )

    def test_set__overwrites_previous_progress(self) -> None:
        store = ProgressStore()
        run_id = uuid4()

        store.set(run_id=run_id, progress=OperatorProgress(current=3, total=10))
        store.set(run_id=run_id, progress=OperatorProgress(current=7, total=10))

        assert store.get(run_id=run_id) == OperatorProgress(current=7, total=10)

    def test_set__runs_are_independent(self) -> None:
        store = ProgressStore()
        first_run_id = uuid4()
        second_run_id = uuid4()

        store.set(run_id=first_run_id, progress=OperatorProgress(current=1, total=10))
        store.set(run_id=second_run_id, progress=OperatorProgress(current=5, total=20))

        assert store.get(run_id=first_run_id) == OperatorProgress(current=1, total=10)
        assert store.get(run_id=second_run_id) == OperatorProgress(current=5, total=20)

    def test_clear(self) -> None:
        store = ProgressStore()
        run_id = uuid4()
        store.set(run_id=run_id, progress=OperatorProgress(current=3, total=10))

        store.clear(run_id=run_id)

        assert store.get(run_id=run_id) is None

    def test_clear__unknown_run(self) -> None:
        store = ProgressStore()

        # Clearing a run that was never recorded must not raise.
        store.clear(run_id=uuid4())
