"""Serve `ColorQueryEmbedder` on a fixed port, for the remote embedder e2e test.

`index_remote_embedder.py` runs this script in a subprocess. The server also answers the
number of embed calls on `EMBED_COUNT_PATH`, so a test can check that a search reached it.
"""

from __future__ import annotations

import uvicorn
from lightly_studio_serve import server

from tests.embed.remote.color_embedder import ColorQueryEmbedder

HOST = "127.0.0.1"
PORT = 8011
API_KEY = "e2e-remote-embedder-key"
EMBED_COUNT_PATH = "/test/embed-count"


def main() -> None:
    """Serve until the process stops."""
    embedder = ColorQueryEmbedder()
    app = server.create_app(embedder=embedder, api_key=API_KEY)

    def embed_count() -> dict[str, int]:
        """Answer the number of embed calls so far."""
        return {"count": embedder.call_count}

    app.add_api_route(path=EMBED_COUNT_PATH, endpoint=embed_count, methods=["GET"])
    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")


if __name__ == "__main__":
    main()
