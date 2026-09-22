"""Camera Station: the live camera page that collects frames and shows the live model.

This is the only part of the demo with its own web UI. It runs as a small FastAPI app
on its own port, next to the LightlyStudio server. Everything after the frames land in
the dataset happens in LightlyStudio itself.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from pydantic import BaseModel

from lightly_studio.examples.camera_plugins_demo import camera as camera_module
from lightly_studio.examples.camera_plugins_demo.demo_app import CameraDemo

logger = logging.getLogger(__name__)

_STREAM_FPS = 20.0
_BOUNDARY = "frame"


class BookmarkRequest(BaseModel):
    """Body of a bookmark request."""

    tag: str = ""


class SourceRequest(BaseModel):
    """Body of a camera source change."""

    source: str


class DeployRequest(BaseModel):
    """Body of a deployment request."""

    model: str = "latest"
    threshold: float = 0.5


class AutoCaptureRequest(BaseModel):
    """Body of the auto-capture toggle."""

    enabled: bool


def create_app(demo: CameraDemo) -> FastAPI:
    """Build the Camera Station web app for a demo session."""
    app = FastAPI(title="LightlyStudio Camera Station", docs_url=None, redoc_url=None)
    _add_page_routes(app=app, demo=demo)
    _add_control_routes(app=app, demo=demo)
    return app


def _add_page_routes(app: FastAPI, demo: CameraDemo) -> None:
    page = Path(__file__).parent / "station.html"

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return page.read_text()

    @app.get("/stream.mjpg")
    def stream() -> StreamingResponse:
        return StreamingResponse(
            _frames(demo=demo),
            media_type=f"multipart/x-mixed-replace; boundary={_BOUNDARY}",
            headers={"Cache-Control": "no-store"},
        )

    @app.get("/api/state")
    def state() -> dict[str, Any]:
        return demo.state()


def _add_control_routes(app: FastAPI, demo: CameraDemo) -> None:
    @app.post("/api/bookmark")
    def bookmark(request: BookmarkRequest) -> dict[str, str]:
        try:
            file_name = demo.bookmark(tags=[request.tag] if request.tag else [])
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return {"file_name": file_name}

    @app.post("/api/source")
    def set_source(request: SourceRequest) -> dict[str, str]:
        demo.camera.set_source(source=request.source)
        demo.dispatcher.log(channel="camera", message=f"Source set to {request.source}")
        return {"source": request.source}

    @app.post("/api/deploy")
    def deploy(request: DeployRequest) -> dict[str, str]:
        try:
            message = demo.deploy(model=request.model, threshold=request.threshold)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"message": message}

    @app.post("/api/undeploy")
    def undeploy() -> dict[str, str]:
        demo.stop_deployment()
        return {"message": "stopped"}

    @app.post("/api/auto-capture")
    def auto_capture(request: AutoCaptureRequest) -> dict[str, bool]:
        demo.detector.set_auto_capture(enabled=request.enabled)
        return {"enabled": request.enabled}

    @app.get("/bookmarks/{file_name}")
    def bookmark_image(file_name: str) -> FileResponse:
        return _safe_file(directory=demo.bookmarks.bookmarks_dir, file_name=file_name)

    @app.get("/runs/{run_name}/examples/{file_name}")
    def run_example(run_name: str, file_name: str) -> FileResponse:
        directory = demo.trainings.runs_dir / run_name / "train" / "image_examples"
        return _safe_file(directory=directory, file_name=file_name)


def serve_in_background(demo: CameraDemo, port: int) -> uvicorn.Server:
    """Run the Camera Station in a daemon thread and return the server."""
    config = uvicorn.Config(
        app=create_app(demo=demo), host="0.0.0.0", port=port, log_level="warning"
    )
    server = uvicorn.Server(config=config)
    thread = threading.Thread(target=server.run, name="camera-station", daemon=True)
    thread.start()
    return server


def _frames(demo: CameraDemo) -> Iterator[bytes]:
    last_index = -1
    min_interval = 1.0 / _STREAM_FPS
    while True:
        frame = demo.camera.wait_for_frame(after_index=last_index, timeout=2.0)
        if frame is None:
            time.sleep(0.1)
            continue
        last_index = frame.index
        image = frame.image
        if demo.detector.status().active:
            image = demo.detector.draw_overlay(image=image)
        try:
            jpeg = camera_module.encode_jpeg(image=image)
        except ValueError:
            continue
        yield (
            (
                f"--{_BOUNDARY}\r\nContent-Type: image/jpeg\r\nContent-Length: {len(jpeg)}\r\n\r\n"
            ).encode()
            + jpeg
            + b"\r\n"
        )
        time.sleep(min_interval)


def _safe_file(directory: Path, file_name: str) -> FileResponse:
    path = (directory / file_name).resolve()
    if not path.is_file() or directory.resolve() not in path.parents:
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(path)
