"""Example of how to load samples from path with the dataset class."""

from __future__ import annotations

import asyncio

from environs import Env

import lightly_studio as ls
from lightly_studio import db_manager

# Read environment variables
env = Env()
env.read_env()

# Cleanup an existing database
db_manager.connect(cleanup_existing=True)

# Define the path to the dataset directory
dataset_path = env.path("EXAMPLES_DATASET_PATH", "/path/to/your/dataset")

# Create a Dataset from a path
dataset = ls.Dataset.create()
dataset.add_images_from_path(
    path="gs://lightly-edge-datasets/diversity_eval", process_in_background=True, embed=False
)


async def dummy_loop() -> None:
    """Docstring."""
    await asyncio.sleep(500.0)


ls.start_gui(dummy_loop)

# Uncomment to showcase Lukas' embeddings in the background using asyncio

# import logging
# import aioprocessing
# import numpy
# from numpy.typing import NDArray
#
# queue: aioprocessing.Queue[NDArray[numpy.float32]] = aioprocessing.AioQueue()
# process = dataset.add_images_from_path(
#     path=dataset_path,
#     process_in_background=False,
#     embed=True,
#     queue=queue,
# )
# # process is returned when we supply the `queue` argument
# assert process is not None
#
#
# async def embedding_coroutine() -> None:
#     """Docstring."""
#     while True:
#         embeddings = await queue.coro_get()
#         logging.info(f"Got embeddings of shape {embeddings.shape} in asyncio loop")
#         await dataset.store_embeddings(embeddings)
#
#
# ls.start_gui(embedding_coroutine)
# process.join()
