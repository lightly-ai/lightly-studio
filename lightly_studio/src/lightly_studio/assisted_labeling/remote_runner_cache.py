"""Keeps the runners of the labeling servers that datasets save.

A runner is built from a saved configuration: a URL and an API key. Building one reads
the describe endpoint of the server, so the cache keeps the runner for later requests. A
server that cannot be connected is remembered for a short time, so the GUI does not wait
for it on every request.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from uuid import UUID

from lightly_studio.assisted_labeling.remote_labeling_model_runner import (
    RemoteLabelingModelError,
    RemoteLabelingModelRunner,
)
from lightly_studio.embed.remote import connection
from lightly_studio.models.labeling_model import LabelingModelTable

# The time before a server that could not be connected is tried again.
RETRY_DELAY_SECONDS = 30.0


@dataclass(frozen=True)
class RemoteLabelingModelConfig:
    """The saved configuration of one labeling model on a server, in one dataset.

    The class is frozen, so two configurations compare by value. The cache builds a
    runner again when the saved configuration changes.

    Attributes:
        dataset_id: The dataset that saves the configuration.
        model_id: The ID of the labeling model that the server must serve.
        url: The base URL of the server.
        api_key: The bearer token of the server, kept out of a repr.
    """

    dataset_id: UUID
    model_id: str
    url: str
    api_key: str | None = field(default=None, repr=False)


class RemoteRunnerCache:
    """Builds each runner once for a configuration, and remembers a failure for a while."""

    def __init__(self) -> None:
        """Create an empty cache."""
        self._config_to_runner: dict[RemoteLabelingModelConfig, RemoteLabelingModelRunner] = {}
        self._config_to_failure: dict[RemoteLabelingModelConfig, tuple[float, str]] = {}
        self._lock = threading.Lock()

    def get(self, config: RemoteLabelingModelConfig) -> RemoteLabelingModelRunner:
        """Return the runner of the configuration, and build it if there is none.

        Raises:
            RemoteLabelingModelError: If the server cannot be connected, or serves
                another model than the saved one.
        """
        # One lock for the whole build. Two requests for one server then read its
        # describe endpoint once.
        with self._lock:
            runner = self._config_to_runner.get(config)
            if runner is not None:
                return runner
            failure = self._config_to_failure.get(config)
            if failure is not None and time.monotonic() - failure[0] < RETRY_DELAY_SECONDS:
                raise RemoteLabelingModelError(failure[1])
            try:
                runner = build_runner(config=config)
            except RemoteLabelingModelError as error:
                self._config_to_failure[config] = (time.monotonic(), str(error))
                raise
            self._config_to_failure.pop(config, None)
            self._config_to_runner[config] = runner
            return runner


_cache = RemoteRunnerCache()


def get_cache() -> RemoteRunnerCache:
    """Return the process-wide cache of remote runners."""
    return _cache


def from_labeling_model(labeling_model: LabelingModelTable) -> RemoteLabelingModelConfig:
    """Read the configuration of a saved labeling model row."""
    return RemoteLabelingModelConfig(
        dataset_id=labeling_model.dataset_id,
        model_id=labeling_model.model_id,
        url=labeling_model.url,
        api_key=labeling_model.api_key,
    )


def build_runner(config: RemoteLabelingModelConfig) -> RemoteLabelingModelRunner:
    """Connect to the labeling server that the configuration names.

    The runner keeps its client open for the lifetime of the process.

    Raises:
        RemoteLabelingModelError: If the server cannot be connected, or serves another
            model than the saved one.
    """
    runner = connect(url=config.url, api_key=config.api_key)
    if runner.model_id != config.model_id:
        raise RemoteLabelingModelError(
            f"The labeling server at {config.url!r} serves the model {runner.model_id!r}. "
            f"The dataset saved {config.model_id!r}. Register the server again."
        )
    return runner


def connect(url: str, api_key: str | None) -> RemoteLabelingModelRunner:
    """Open a client against ``url`` and build the runner of its labeling model.

    Raises:
        RemoteLabelingModelError: If the URL does not parse, or the server cannot be
            connected.
    """
    try:
        client = connection.build_client(url=url)
    except ValueError as error:
        # `httpx.InvalidURL` is a `ValueError`.
        raise RemoteLabelingModelError(
            f"The labeling server URL {url!r} does not parse."
        ) from error
    try:
        return RemoteLabelingModelRunner.connect(client=client, api_key=api_key)
    except Exception:
        client.close()
        raise
