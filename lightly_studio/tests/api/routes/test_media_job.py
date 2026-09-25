from __future__ import annotations

import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from pytest_mock import MockerFixture
from starlette.requests import Request
from starlette.types import Message

from lightly_studio.api.routes import media_job
from lightly_studio.utils import executor


def test_run_media_job() -> None:
    result = asyncio.run(
        media_job.run_media_job(
            request=_make_request(disconnect=False),
            thread_name_prefix="test_media_job",
            job=lambda: "done",
        )
    )

    assert result == "done"


def test_run_media_job__disconnect_skips_queued_job(mocker: MockerFixture) -> None:
    # A single worker, held busy, keeps the job under test in the queue.
    single_worker = ThreadPoolExecutor(max_workers=1)
    mocker.patch.object(executor, "get_media_executor", return_value=single_worker)
    release_worker = threading.Event()
    single_worker.submit(release_worker.wait)
    job_ran = threading.Event()

    try:
        result = asyncio.run(
            media_job.run_media_job(
                request=_make_request(disconnect=True),
                thread_name_prefix="test_media_job",
                job=job_ran.set,
            )
        )
    finally:
        release_worker.set()
        single_worker.shutdown(wait=True)

    assert result is None
    assert not job_ran.is_set()


def test_run_media_job__raises_job_exception() -> None:
    def failing_job() -> None:
        raise ValueError("broken frame")

    with pytest.raises(ValueError, match="broken frame"):
        asyncio.run(
            media_job.run_media_job(
                request=_make_request(disconnect=False),
                thread_name_prefix="test_media_job",
                job=failing_job,
            )
        )


def _make_request(disconnect: bool) -> Request:
    """Create a GET request whose client disconnects, or stays connected."""
    messages: list[Message] = [{"type": "http.request", "body": b"", "more_body": False}]
    if disconnect:
        messages.append({"type": "http.disconnect"})

    async def receive() -> Message:
        if messages:
            return messages.pop(0)
        # A connected client sends no more messages.
        never_done: asyncio.Future[Message] = asyncio.get_running_loop().create_future()
        return await never_done

    return Request(scope={"type": "http"}, receive=receive)
