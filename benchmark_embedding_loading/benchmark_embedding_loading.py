"""Benchmark embedding loading via the API server.

This script connects to an existing database (lexica_benchmark.db), starts the
Lightly Studio API in the background, and measures the time to load embeddings
via the /api/embeddings2d/default endpoint.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

import lightly_studio as ls
from lightly_studio import db_manager
from lightly_studio.dataset import embedding_utils, env
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter

DB_FILE = "lexica_benchmark.db"
HEALTH_URL = f"{env.APP_URL}/healthz"
EMBEDDINGS_URL = f"{env.APP_URL}/api/embeddings2d/default"


def _wait_for_server(url: str, timeout_s: float = 30.0, interval_s: float = 0.2) -> None:
    start = time.time()
    while True:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return
        except Exception:
            pass

        if time.time() - start > timeout_s:
            raise RuntimeError(f"Server did not become healthy within {timeout_s:.1f}s")

        time.sleep(interval_s)


def _post_json(url: str, payload: dict) -> tuple[int, bytes]:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request) as response:
            body = response.read()
            return response.status, body
    except urllib.error.HTTPError as exc:
        body = exc.read()
        return exc.code, body


def main() -> None:
    db_manager.connect(cleanup_existing=False, db_file=DB_FILE)
    dataset = ls.ImageDataset.load(name="default")

    if not embedding_utils.collection_has_embeddings(
        session=dataset.session, collection_id=dataset.dataset_id
    ):
        raise RuntimeError("Dataset has no embeddings. Create embeddings before benchmarking.")

    ls.start_gui_background()

    try:
        _wait_for_server(HEALTH_URL)

        image_filter = ImageFilter(sample_filter=SampleFilter(collection_id=dataset.dataset_id))
        payload = {"filters": image_filter.model_dump(mode="json")}

        print("Starting benchmark for embedding loading...")
        start = time.time()
        status, _body = _post_json(EMBEDDINGS_URL, payload)
        end = time.time()

        if status >= 400:
            raise RuntimeError(f"Request failed with status {status}")

        print(f"Time taken to load embeddings: {end - start:.2f} seconds")
    finally:
        ls.stop_gui_background()


if __name__ == "__main__":
    main()
