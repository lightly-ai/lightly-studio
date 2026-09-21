"""Synchronous model HTTP transport for the local auto-labeling prototype."""

from __future__ import annotations

import contextlib
import ipaddress
import logging
import math
import os
import time
from datetime import datetime, timezone
from email import utils
from http import HTTPStatus
from urllib import parse

import requests
from pydantic import ValidationError

from lightly_studio.models.auto_labeling import AnnotationDescriptor, AnnotationResponse, Task

MAX_ATTEMPTS = 3
MAX_RETRY_DELAY_SECONDS = 60
MAX_ERROR_DETAIL_LENGTH = 500
logger = logging.getLogger(__name__)


class AnnotationModelClient:
    """Discover a configured model and send bounded multipart requests."""

    def __init__(self) -> None:
        """Read the prototype endpoint and optional bearer key from the environment."""
        self.endpoint = os.environ.get(
            "LIGHTLY_STUDIO_ANNOTATION_URL", "http://localhost:8080"
        ).rstrip("/")
        key = os.environ.get("LIGHTLY_STUDIO_ANNOTATION_API_KEY", "")
        _validate_endpoint(endpoint=self.endpoint, key=key)
        self.headers = {"Authorization": f"Bearer {key}"} if key else {}

    def describe(self) -> AnnotationDescriptor:
        """Read current readiness and capabilities without exposing credentials."""
        try:
            response = requests.get(
                url=f"{self.endpoint}/v1/describe",
                headers=self.headers,
                timeout=5,
                allow_redirects=False,
            )
            _check_status(response=response)
            descriptor = AnnotationDescriptor.model_validate_json(response.content)
            logger.info(
                "Annotation model discovery endpoint=%s model_key=%s "
                "supported_conditioning=%s capabilities=%s",
                self.endpoint,
                descriptor.model_key,
                descriptor.supported_conditioning,
                descriptor.capabilities,
            )
            return descriptor
        except requests.RequestException as exc:
            raise ValueError(
                "Cannot reach the annotation model. Check its server and endpoint."
            ) from exc
        except ValidationError as exc:
            raise ValueError(
                "The annotation model returned an invalid discovery response."
            ) from exc

    def infer(
        self,
        descriptor: AnnotationDescriptor,
        task: Task,
        images: list[bytes],
        conditioning: str,
    ) -> AnnotationResponse:
        """Infer a batch, splitting size failures and validating result alignment."""
        request = requests.Request(
            method="POST",
            url=f"{self.endpoint}/v1/annotate/{task}/images/bytes",
            headers=self.headers,
            files=[
                ("images", ("image", content, "application/octet-stream")) for content in images
            ],
            data={"conditioning": conditioning},
        ).prepare()
        body_size = int(request.headers.get("Content-Length", "0"))
        if (
            len(images) > descriptor.limits.max_batch_size
            or body_size > descriptor.limits.max_request_bytes
        ):
            return self._split(
                descriptor=descriptor, task=task, images=images, conditioning=conditioning
            )
        response = self._send(request=request)
        if response.status_code == HTTPStatus.REQUEST_ENTITY_TOO_LARGE:
            return self._split(
                descriptor=descriptor, task=task, images=images, conditioning=conditioning
            )
        if response.status_code == HTTPStatus.NOT_IMPLEMENTED:
            self.describe()
        _check_status(response=response)
        try:
            result = AnnotationResponse.model_validate_json(response.content)
        except ValidationError as exc:
            raise ValueError("The annotation model returned invalid predictions.") from exc
        _validate_response(result=result, model_key=descriptor.model_key, count=len(images))
        return result

    def _split(
        self, descriptor: AnnotationDescriptor, task: Task, images: list[bytes], conditioning: str
    ) -> AnnotationResponse:
        if len(images) <= 1:
            raise ValueError("One image exceeds the annotation model request-size limit.")
        middle = len(images) // 2
        left = self.infer(
            descriptor=descriptor, task=task, images=images[:middle], conditioning=conditioning
        )
        right = self.infer(
            descriptor=descriptor, task=task, images=images[middle:], conditioning=conditioning
        )
        return AnnotationResponse(
            model_key=descriptor.model_key,
            kept_indices=left.kept_indices + [middle + index for index in right.kept_indices],
            results=left.results + right.results,
        )

    def _send(self, request: requests.PreparedRequest) -> requests.Response:
        try:
            with requests.Session() as session:
                for attempt in range(MAX_ATTEMPTS):
                    response = session.send(request=request, timeout=120, allow_redirects=False)
                    if (
                        response.status_code
                        not in (HTTPStatus.TOO_MANY_REQUESTS, HTTPStatus.SERVICE_UNAVAILABLE)
                        or attempt == MAX_ATTEMPTS - 1
                    ):
                        return response
                    delay = _retry_delay(value=response.headers.get("Retry-After"), attempt=attempt)
                    if delay > MAX_RETRY_DELAY_SECONDS:
                        raise ValueError(
                            "The annotation model is busy. Retry after its requested delay."
                        )
                    time.sleep(delay)
        except requests.RequestException as exc:
            raise ValueError(
                "Annotation inference failed. Check the model server and retry."
            ) from exc
        raise RuntimeError("The bounded model request loop did not return a response.")


def _validate_endpoint(endpoint: str, key: str) -> None:
    url = parse.urlsplit(endpoint)
    if (
        url.scheme not in ("http", "https")
        or not url.hostname
        or url.username
        or url.password
        or url.query
        or url.fragment
    ):
        raise ValueError(
            "Configure a plain HTTP(S) annotation endpoint without credentials or query parameters."
        )
    loopback = url.hostname.lower() == "localhost"
    with contextlib.suppress(ValueError):
        loopback = loopback or ipaddress.ip_address(url.hostname).is_loopback
    if not loopback and not key:
        raise ValueError("Set LIGHTLY_STUDIO_ANNOTATION_API_KEY for a non-loopback model endpoint.")


def _check_status(response: requests.Response) -> None:
    if response.status_code != HTTPStatus.OK:
        detail = response.text.strip()
        if len(detail) > MAX_ERROR_DETAIL_LENGTH:
            detail = f"{detail[:MAX_ERROR_DETAIL_LENGTH]}..."
        suffix = f" Response: {detail}" if detail else ""
        raise ValueError(
            f"Annotation model returned HTTP {response.status_code}. "
            f"Check its configuration and readiness.{suffix}"
        )


def _validate_response(result: AnnotationResponse, model_key: str, count: int) -> None:
    if result.model_key != model_key:
        raise ValueError(
            "The annotation model identity changed during inference. Check the connection again."
        )
    if len(result.results) != len(result.kept_indices) or len(set(result.kept_indices)) != len(
        result.kept_indices
    ):
        raise ValueError("The annotation model returned inconsistent result indices.")
    if any(index >= count for index in result.kept_indices):
        raise ValueError("The annotation model returned an out-of-range result index.")


def _retry_delay(value: str | None, attempt: int) -> float:
    if value is None:
        return float(2**attempt)
    try:
        delay = float(value)
        return max(0, delay) if math.isfinite(delay) else float(2**attempt)
    except ValueError:
        try:
            return max(
                0, (utils.parsedate_to_datetime(value) - datetime.now(timezone.utc)).total_seconds()
            )
        except (ValueError, TypeError):
            return float(2**attempt)
