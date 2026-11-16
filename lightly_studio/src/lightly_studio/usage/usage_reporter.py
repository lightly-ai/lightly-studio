"""Reporting of paid service usage to a central service.

Every paid service (AI-assisted labeling, embedding) reports through this module. A
real-time call is one event. A background job reports one event per processed chunk,
with the job ID and the chunk size as quantity.

Reports are sent only when both `LIGHTLY_STUDIO_USAGE_REPORT_URL` and
`LIGHTLY_STUDIO_SERVICE_TOKEN` are set. A background thread sends them in batches
of up to 500 events, so a slow or unreachable receiver never delays the service that
reports. A batch that fails for a reason that can be transient is retried twice; the
receiver ignores repeated event IDs, so a retry cannot count an event twice.

Reporting is best effort: it never raises, so a failed report cannot break the service
that reports. Events are dropped when the queue is full, when all attempts fail, and when
the process exits before they are sent.
"""

from __future__ import annotations

import json
import logging
import queue
import threading
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from http import HTTPStatus
from uuid import UUID

import requests

from lightly_studio.dataset import env

logger = logging.getLogger(__name__)

REPORT_TIMEOUT_S = 2.0
MAX_EVENTS_PER_REPORT = 500
MAX_QUEUED_EVENTS = 10_000
RETRY_DELAYS_S = (1.0, 5.0)
"""Pauses before the second and the third attempt to send a batch."""

_queue: queue.Queue[UsageEvent] = queue.Queue(maxsize=MAX_QUEUED_EVENTS)
_worker: threading.Thread | None = None
_worker_lock = threading.Lock()


class UsageService(str, Enum):
    """The paid service that was used."""

    AUTOLABELING = "autolabeling"
    EMBEDDING = "embedding"


class UsageMode(str, Enum):
    """Whether a user waited for the result or a background job did the work."""

    REALTIME = "realtime"
    BATCH = "batch"


class UsageUnit(str, Enum):
    """The unit the quantity is counted in."""

    REQUEST = "request"
    IMAGE = "image"
    TOKEN = "token"


@dataclass(frozen=True)
class UsageEvent:
    """One real-time call, or one processed chunk of a background job.

    Attributes:
        event_id: Unique ID of the event. The receiver ignores repeated IDs.
        occurred_at: Timezone-aware start time of the call or chunk.
        user_email: Email of the user who triggered the call or started the job.
        service: The paid service.
        operation: What the service did, in snake case, for example `embed_image`.
        mode: Real-time call or background job.
        vendor: Who bills the call, for example `fal`.
        model: The model or vendor endpoint, for example `fal-ai/sam-3/image-rle`.
        unit: The unit `quantity` is counted in.
        quantity: Billable units in this event.
        success: Whether the call or chunk succeeded.
        job_id: ID of the background job. Required in batch mode.
        collection_id: Collection the work was done in, if any.
        latency_ms: Duration of a real-time call in milliseconds.
        details: Small service-specific facts, at most 2 KB as JSON. Never prompts or
            image data.
    """

    event_id: UUID
    occurred_at: datetime
    user_email: str | None
    service: UsageService
    operation: str
    mode: UsageMode
    vendor: str
    model: str
    unit: UsageUnit
    quantity: int
    success: bool
    job_id: UUID | None = None
    collection_id: UUID | None = None
    latency_ms: float | None = None
    details: dict[str, object] | None = None

    def to_json(self) -> dict[str, object]:
        """Returns the event as a JSON-serializable dictionary."""
        return {
            "event_id": str(self.event_id),
            "occurred_at": self.occurred_at.isoformat(),
            "user_email": self.user_email,
            "service": self.service.value,
            "operation": self.operation,
            "mode": self.mode.value,
            "job_id": None if self.job_id is None else str(self.job_id),
            "vendor": self.vendor,
            "model": self.model,
            "unit": self.unit.value,
            "quantity": self.quantity,
            "success": self.success,
            "collection_id": None if self.collection_id is None else str(self.collection_id),
            "latency_ms": self.latency_ms,
            "details": self.details,
        }


def report(events: Sequence[UsageEvent]) -> None:
    """Queues the events for sending if reporting is configured. Never raises or blocks."""
    url = env.LIGHTLY_STUDIO_USAGE_REPORT_URL
    token = env.LIGHTLY_STUDIO_SERVICE_TOKEN
    if not url or not token:
        return
    _start_worker(url=url, token=token)
    for index, event in enumerate(events):
        # Checked here so that one invalid event cannot drop the whole batch it is sent in.
        if not _is_serializable(event=event):
            continue
        try:
            _queue.put_nowait(event)
        except queue.Full:
            logger.warning(
                "The usage report queue is full. Dropped %d events.", len(events) - index
            )
            return


def send(
    events: Sequence[UsageEvent],
    url: str,
    token: str,
    session: requests.Session,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    """Posts the events to the URL with the token as bearer token. Never raises.

    Retries twice after a connection error, a timeout, status 429 or a 5xx status. Does
    not follow redirects.

    Args:
        events: The events to send, at most 500.
        url: URL of the usage endpoint.
        token: Token that identifies this deployment to the endpoint.
        session: HTTP session for the request.
        sleep: Waits the given number of seconds between attempts.
    """
    try:
        payload = {"events": [event.to_json() for event in events]}
    except Exception:
        logger.warning("Could not serialize usage of %d events.", len(events), exc_info=True)
        return
    for retry_delay_s in (*RETRY_DELAYS_S, None):
        try:
            response = session.post(
                url=url,
                json=payload,
                headers={"Authorization": f"Bearer {token}"},
                timeout=REPORT_TIMEOUT_S,
                # A redirect would send the events to a host the URL does not name.
                allow_redirects=False,
            )
        except requests.RequestException as error:
            failure = str(error)
            transient = True
        except Exception:
            logger.warning("Could not report usage of %d events.", len(events), exc_info=True)
            return
        else:
            if response.status_code < HTTPStatus.MULTIPLE_CHOICES:
                return
            failure = f"status {response.status_code}"
            transient = (
                response.status_code == HTTPStatus.TOO_MANY_REQUESTS
                or response.status_code >= HTTPStatus.INTERNAL_SERVER_ERROR
            )
        if not transient or retry_delay_s is None:
            logger.warning("Could not report usage of %d events: %s", len(events), failure)
            return
        sleep(retry_delay_s)


def _is_serializable(event: UsageEvent) -> bool:
    try:
        # Requests rejects NaN and infinity when it encodes the request.
        json.dumps(event.to_json(), allow_nan=False)
    except Exception:
        logger.warning("Dropped a usage event that cannot be serialized.", exc_info=True)
        return False
    return True


def _start_worker(url: str, token: str) -> None:
    global _worker  # noqa: PLW0603
    with _worker_lock:
        if _worker is not None:
            return
        # A daemon thread does not delay the exit of the process.
        worker = threading.Thread(
            target=_run_worker,
            kwargs={"url": url, "token": token},
            name="usage-report",
            daemon=True,
        )
        try:
            worker.start()
        except RuntimeError:
            # The next report tries again and then sends the queued events.
            logger.warning("Could not start the usage report thread.", exc_info=True)
            return
        _worker = worker


def _run_worker(url: str, token: str) -> None:
    session = requests.Session()
    while True:
        events = _take_events(event_queue=_queue)
        send(events=events, url=url, token=token, session=session)


def _take_events(event_queue: queue.Queue[UsageEvent]) -> list[UsageEvent]:
    """Waits for an event, then returns it with the queued events up to the batch size."""
    events = [event_queue.get()]
    while len(events) < MAX_EVENTS_PER_REPORT:
        try:
            events.append(event_queue.get_nowait())
        except queue.Empty:
            break
    return events
