"""Serve a dataset whose search embeds queries on a remote embedding server.

The images are embedded locally by an embedder that implements no query capability, so
text and image search can only embed on the server that `remote_embedder_server.py` runs.
"""

from __future__ import annotations

import atexit
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
from pathlib import Path

import remote_embedder_server

import lightly_studio as ls
from tests.embed.remote import color_embedder, threaded_server
from tests.embed.remote.color_embedder import ColorImagePathEmbedder


def _exit_on_sigterm(signum: int, _frame: object) -> None:
    """Exit normally, so that `atexit` stops the embedding server."""
    sys.exit(128 + signum)


# uvicorn re-raises SIGTERM after shutdown, which skips `atexit` and leaks the server.
signal.signal(signal.SIGTERM, _exit_on_sigterm)

# A server left over from an earlier run would answer in place of the new one.
with socket.socket() as probe:
    if probe.connect_ex((remote_embedder_server.HOST, remote_embedder_server.PORT)) == 0:
        raise RuntimeError(f"Port {remote_embedder_server.PORT} is in use, stop what holds it.")
server_process = subprocess.Popen([sys.executable, remote_embedder_server.__file__])
atexit.register(server_process.terminate)
server_url = f"http://{remote_embedder_server.HOST}:{remote_embedder_server.PORT}"
threaded_server.wait_until_ready(url=server_url, api_key=remote_embedder_server.API_KEY)
if server_process.poll() is not None:
    raise RuntimeError(f"The embedding server exited with code {server_process.returncode}.")

ls.db_manager.connect(cleanup_existing=True)

image_directory = Path(tempfile.mkdtemp())
atexit.register(shutil.rmtree, image_directory)
color_embedder.write_color_images(directory=image_directory)
ls.register_default_embedder(embedder=ColorImagePathEmbedder())
dataset = ls.ImageDataset.create()
dataset.add_images_from_path(path=image_directory)
ls.register_remote_embedder(dataset=dataset, url=server_url, api_key=remote_embedder_server.API_KEY)

# The GUI serves on port 8001
ls.start_gui()
