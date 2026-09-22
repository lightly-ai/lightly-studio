"""Run LightlyTrain object detection trainings and follow their progress."""

from __future__ import annotations

import json
import logging
import re
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)

STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"

_POLL_INTERVAL_S = 1.0
_STEP_PATTERN = re.compile(r"Train Step\s+(\d+)/(\d+)")
_LOSS_PATTERN = re.compile(r"train_loss:\s*([0-9.]+)")
_METRIC_PATTERN = re.compile(r"\|\s*(val_metric/[a-z0-9_]+)\s*\|\s*([0-9.]+)")


@dataclass
class TrainingConfig:
    """Everything needed to start one training run.

    Attributes:
        run_name: Short name of the run, also used as the prediction annotation source.
        model: LightlyTrain model name or checkpoint path.
        steps: Number of optimizer steps.
        batch_size: Number of images per step.
        image_size: Length of the square input the model trains on, in pixels.
        accelerator: "cpu", "gpu", "mps" or "auto".
        precision: Lightning precision string.
        num_workers: Dataloader workers.
        train_sample_ids: LightlyStudio sample IDs in the train split.
        val_sample_ids: LightlyStudio sample IDs in the validation split.
        annotation_source: Annotation source the training labels come from.
    """

    run_name: str
    model: str
    steps: int
    batch_size: int
    image_size: int
    accelerator: str
    precision: str
    num_workers: int
    train_sample_ids: list[UUID]
    val_sample_ids: list[UUID]
    annotation_source: str


@dataclass
class RunState:
    """Live state of a training run, shown by the Camera Station page."""

    run_name: str
    model: str
    status: str
    started_at: float
    steps: int
    step: int = 0
    loss: float | None = None
    finished_at: float | None = None
    train_image_count: int = 0
    val_image_count: int = 0
    annotation_source: str = ""
    class_names: list[str] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)
    message: str = ""
    evaluation: str = ""

    @property
    def progress(self) -> float:
        """Fraction of steps done, in [0, 1]."""
        return min(1.0, self.step / self.steps) if self.steps else 0.0


class TrainingManager:
    """Starts training subprocesses and tracks their progress.

    One run at a time. Each run gets a directory under `runs_dir`:

    ```text
    <runs_dir>/<run_name>/run.json      training configuration
    <runs_dir>/<run_name>/state.json    progress and metrics, updated while training
    <runs_dir>/<run_name>/data/         exported COCO annotations
    <runs_dir>/<run_name>/train/        LightlyTrain output: checkpoints, logs, examples
    ```
    """

    def __init__(self, runs_dir: Path, on_completed: Callable[[RunState], None] | None = None):
        """Create the manager and load the runs of earlier sessions."""
        self.runs_dir = runs_dir
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self.on_completed = on_completed
        """Called after a run finishes, for example to evaluate it in LightlyStudio."""
        self._states: dict[str, RunState] = {}
        self._process: subprocess.Popen[bytes] | None = None
        self._lock = threading.Lock()
        self._load_previous_runs()

    def start(self, config: TrainingConfig) -> RunState:
        """Start a training run in a subprocess and return its initial state.

        Raises:
            RuntimeError: If another run is still training.
        """
        with self._lock:
            if self.is_running():
                raise RuntimeError("A training run is already in progress.")
            run_dir = self.run_dir(run_name=config.run_name)
            worker_config = {
                "out": str(run_dir / "train"),
                "train_annotations": str(run_dir / "data" / "train.json"),
                "val_annotations": str(run_dir / "data" / "val.json"),
                "model": config.model,
                "steps": config.steps,
                "batch_size": config.batch_size,
                "image_size": config.image_size,
                "accelerator": config.accelerator,
                "precision": config.precision,
                "num_workers": config.num_workers,
            }
            config_path = run_dir / "run.json"
            config_path.write_text(json.dumps({**worker_config, **_ids_to_json(config)}, indent=2))

            state = RunState(
                run_name=config.run_name,
                model=config.model,
                status=STATUS_RUNNING,
                started_at=time.time(),
                steps=config.steps,
                train_image_count=len(config.train_sample_ids),
                val_image_count=len(config.val_sample_ids),
                annotation_source=config.annotation_source,
            )
            self._states[config.run_name] = state
            self._write_state(state=state)

            log_file = (run_dir / "worker.log").open("wb")
            self._process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "lightly_studio.examples.camera_plugins_demo.train_worker",
                    str(config_path),
                ],
                stdout=log_file,
                stderr=subprocess.STDOUT,
            )
            logger.info("Started training run %s (pid %s).", config.run_name, self._process.pid)

        thread = threading.Thread(
            target=self._monitor,
            kwargs={"state": state, "process": self._process, "run_dir": run_dir},
            name=f"training-monitor-{config.run_name}",
            daemon=True,
        )
        thread.start()
        return state

    def is_running(self) -> bool:
        """Return True while a training subprocess is alive."""
        return self._process is not None and self._process.poll() is None

    def run_dir(self, run_name: str) -> Path:
        """Return the directory of a run and create it if needed."""
        run_dir = self.runs_dir / run_name
        (run_dir / "data").mkdir(parents=True, exist_ok=True)
        return run_dir

    def next_run_name(self) -> str:
        """Return the next free run name, such as "model-3"."""
        used = {
            int(m.group(1)) for name in self._states if (m := re.fullmatch(r"model-(\d+)", name))
        }
        return f"model-{max(used) + 1 if used else 1}"

    def states(self) -> list[RunState]:
        """Return all known runs, newest first."""
        return sorted(self._states.values(), key=lambda state: state.started_at, reverse=True)

    def get(self, run_name: str) -> RunState | None:
        """Return the state of one run."""
        return self._states.get(run_name)

    def latest_completed(self) -> RunState | None:
        """Return the most recent run that finished training."""
        return next((s for s in self.states() if s.status == STATUS_COMPLETED), None)

    def checkpoint_path(self, run_name: str) -> Path | None:
        """Return the exported model of a run, preferring the best checkpoint."""
        exported = self.runs_dir / run_name / "train" / "exported_models"
        for name in ("exported_best.pt", "exported_last.pt"):
            if (exported / name).is_file():
                return exported / name
        return None

    def example_images(self, run_name: str) -> list[str]:
        """Return file names of the validation prediction images LightlyTrain wrote."""
        examples = self.runs_dir / run_name / "train" / "image_examples"
        if not examples.is_dir():
            return []
        return sorted(p.name for p in examples.glob("val_predictions_*.jpg"))

    def stop(self) -> None:
        """Terminate a running training subprocess."""
        if self.is_running() and self._process is not None:
            self._process.terminate()

    def _monitor(self, state: RunState, process: subprocess.Popen[bytes], run_dir: Path) -> None:
        train_log = run_dir / "train" / "train.log"
        while process.poll() is None:
            self._read_progress(state=state, train_log=train_log)
            self._write_state(state=state)
            time.sleep(_POLL_INTERVAL_S)

        self._read_progress(state=state, train_log=train_log)
        state.finished_at = time.time()
        if process.returncode == 0:
            state.status = STATUS_COMPLETED
            state.step = state.steps
            minutes = (state.finished_at - state.started_at) / 60
            state.message = f"Trained {state.steps} steps in {minutes:.1f} min."
        else:
            state.status = STATUS_FAILED
            state.message = _failure_reason(worker_log=run_dir / "worker.log")
            logger.error("Training run %s failed: %s", state.run_name, state.message)
        self._write_state(state=state)

        if state.status == STATUS_COMPLETED and self.on_completed is not None:
            try:
                self.on_completed(state)
            except Exception:
                logger.exception("Post-training step failed for %s.", state.run_name)
            self._write_state(state=state)

    def _read_progress(self, state: RunState, train_log: Path) -> None:
        if not train_log.is_file():
            return
        text = train_log.read_text(errors="ignore")
        steps = _STEP_PATTERN.findall(text)
        if steps:
            state.step = int(steps[-1][0])
            state.steps = int(steps[-1][1])
        losses = _LOSS_PATTERN.findall(text)
        if losses:
            state.loss = float(losses[-1])
        for key, value in _METRIC_PATTERN.findall(text):
            state.metrics[key.replace("val_metric/", "")] = float(value)

    def _write_state(self, state: RunState) -> None:
        path = self.runs_dir / state.run_name / "state.json"
        path.write_text(json.dumps(asdict(state), indent=2))

    def _load_previous_runs(self) -> None:
        for state_path in sorted(self.runs_dir.glob("*/state.json")):
            try:
                data = json.loads(state_path.read_text())
                state = RunState(**data)
            except (ValueError, TypeError):
                logger.warning("Ignoring unreadable run state '%s'.", state_path)
                continue
            if state.status == STATUS_RUNNING:
                # The process is gone: this run was interrupted by a restart.
                state.status = STATUS_FAILED
                state.message = "Interrupted by a restart."
            self._states[state.run_name] = state


def _ids_to_json(config: TrainingConfig) -> dict[str, Any]:
    return {
        "run_name": config.run_name,
        "annotation_source": config.annotation_source,
        "train_sample_ids": [str(sample_id) for sample_id in config.train_sample_ids],
        "val_sample_ids": [str(sample_id) for sample_id in config.val_sample_ids],
    }


def _failure_reason(worker_log: Path) -> str:
    if not worker_log.is_file():
        return "Training failed. No log file was written."
    lines = [line.strip() for line in worker_log.read_text(errors="ignore").splitlines()]
    error_lines = [line for line in lines if line and not line.startswith(" ")]
    tail = error_lines[-1] if error_lines else "unknown error"
    return f"Training failed: {tail}"
