"""Initialize environment variables for the dataset module."""

from typing import Optional

from environs import Env

env = Env()
env.read_env()
LIGHTLY_STUDIO_EMBEDDINGS_MODEL_TYPE: str = env.str(
    "LIGHTLY_STUDIO_EMBEDDINGS_MODEL_TYPE", "MOBILE_CLIP"
)
LIGHTLY_STUDIO_EDGE_MODEL_FILE_PATH: str = env.str("EDGE_MODEL_PATH", "./lightly_model.tar")
LIGHTLY_STUDIO_PROTOCOL: str = env.str("LIGHTLY_STUDIO_PROTOCOL", "http")
LIGHTLY_STUDIO_PORT: int = env.int("LIGHTLY_STUDIO_PORT", 8001)
LIGHTLY_STUDIO_HOST: str = env.str("LIGHTLY_STUDIO_HOST", "localhost")
LIGHTLY_STUDIO_DEBUG: bool = env.bool("LIGHTLY_STUDIO_DEBUG", False)

APP_URL = f"{LIGHTLY_STUDIO_PROTOCOL}://{LIGHTLY_STUDIO_HOST}:{LIGHTLY_STUDIO_PORT}"

LIGHTLY_STUDIO_LICENSE_KEY: Optional[str] = env.str("LIGHTLY_STUDIO_LICENSE_KEY", default=None)
