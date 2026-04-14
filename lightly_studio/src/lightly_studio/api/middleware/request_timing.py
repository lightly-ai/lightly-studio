"""Request timing middleware for logging slow requests."""

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class RequestTimingMiddleware(BaseHTTPMiddleware):
    """Middleware to log request execution time with configurable thresholds.

    Logs errors for requests exceeding error_threshold_ms. Optionally fails requests that exceed
    the error threshold.
    """

    def __init__(
        self,
        app: ASGIApp,
        error_threshold_ms: int = 200,
        fail_on_error: bool = False,
    ) -> None:
        """Initialize the middleware with configurable thresholds.

        Args:
            app: The ASGI application.
            error_threshold_ms: Threshold in milliseconds for error logs.
            fail_on_error: If True, fail requests exceeding error_threshold_ms.
        """
        super().__init__(app)
        self.error_threshold_ms = error_threshold_ms
        self.fail_on_error = fail_on_error

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Process the request and log timing information.

        Args:
            request: The incoming request.
            call_next: The next middleware or route handler.

        Returns:
            The response from the application, or a 503 error if the request
            exceeded the error threshold and fail_on_error is True.
        """
        start_time = time.perf_counter()

        if self.fail_on_error:
            # Abort execution if it exceeds the threshold
            timeout_seconds = self.error_threshold_ms / 1000.0
            try:
                response = await asyncio.wait_for(call_next(request), timeout=timeout_seconds)
            except asyncio.TimeoutError:
                duration_ms = (time.perf_counter() - start_time) * 1000
                logger.error(
                    f"Request {request.method} {request.url.path} "
                    f"timed out after {duration_ms:.2f}ms"
                )
                return JSONResponse(
                    status_code=503,
                    content={
                        "detail": f"exceeded {self.error_threshold_ms}ms ({duration_ms:.2f}ms)"
                    },
                )
        else:
            response = await call_next(request)

        duration_ms = (time.perf_counter() - start_time) * 1000

        log_message = (
            f"Request {request.method} {request.url.path} completed in {duration_ms:.2f}ms"
        )

        if duration_ms >= self.error_threshold_ms:
            logger.error(log_message)

        return response
