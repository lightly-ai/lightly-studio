"""Run blocking media work and drop it when the client disconnects."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any, TypeVar

from starlette.requests import Request

from lightly_studio.utils import executor

T = TypeVar("T")


async def run_media_job(
    request: Request,
    thread_name_prefix: str,
    job: Callable[[], T],
) -> T | None:
    """Run a job on the media executor until it completes or the client disconnects.

    Uvicorn does not cancel a request task when its client disconnects. Without this
    check, aborted thumbnail requests keep their executor slot and keep the server
    at its concurrency limit.

    Args:
        request: The request that the job serves.
        thread_name_prefix: The media executor to run the job on.
        job: The blocking function to run.

    Returns:
        The job result, or None if the client disconnected first. A job that has not
        started when the client disconnects does not run.

    Raises:
        Exception: Any exception that the job raises.
    """
    job_future = asyncio.get_running_loop().run_in_executor(
        executor.get_media_executor(thread_name_prefix), job
    )
    disconnect_task = asyncio.ensure_future(_wait_for_disconnect(request=request))
    waiters: set[asyncio.Future[Any]] = {job_future, disconnect_task}
    try:
        await asyncio.wait(waiters, return_when=asyncio.FIRST_COMPLETED)
    finally:
        disconnect_task.cancel()
        # Cancelling the asyncio future also cancels the queued executor job.
        job_future.cancel()

    if job_future.cancelled():
        return None
    return job_future.result()


async def _wait_for_disconnect(request: Request) -> None:
    """Wait until the client closes the connection."""
    while True:
        message = await request.receive()
        if message["type"] == "http.disconnect":
            return
