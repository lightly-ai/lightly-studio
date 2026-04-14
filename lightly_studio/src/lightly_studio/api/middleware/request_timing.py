"""Request timing middleware for logging slow requests."""

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

    Logs warnings for requests exceeding warning_threshold_ms and errors for
    requests exceeding error_threshold_ms. Optionally fails requests that exceed
    the error threshold.
    """

    def __init__(
        self,
        app: ASGIApp,
        warning_threshold_ms: int = 100,
        error_threshold_ms: int = 200,
        fail_on_error: bool = False,
    ) -> None:
        """Initialize the middleware with configurable thresholds.

        Args:
            app: The ASGI application.
            warning_threshold_ms: Threshold in milliseconds for warning logs.
            error_threshold_ms: Threshold in milliseconds for error logs.
            fail_on_error: If True, fail requests exceeding error_threshold_ms.
        """
        super().__init__(app)
        self.warning_threshold_ms = warning_threshold_ms
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
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start_time) * 1000

        log_message = (
            f"Request {request.method} {request.url.path} completed in {duration_ms:.2f}ms"
        )

        if duration_ms >= self.error_threshold_ms:
            logger.error(log_message)
            if self.fail_on_error:
                return JSONResponse(
                    status_code=503,
                    content={
                        "detail": f"Request timeout: exceeded {self.error_threshold_ms}ms threshold ({duration_ms:.2f}ms)"
                    },
                )
        elif duration_ms >= self.warning_threshold_ms:
            logger.warning(log_message)
        else:
            logger.debug(log_message)

        return response
