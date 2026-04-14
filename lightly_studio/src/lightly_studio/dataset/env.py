"""Initialize environment variables for the dataset module."""

from pathlib import Path
from typing import Optional

from environs import Env

env = Env()
env.read_env()
LIGHTLY_STUDIO_EMBEDDINGS_MODEL_TYPE: str = env.str(
    "LIGHTLY_STUDIO_EMBEDDINGS_MODEL_TYPE", "MOBILE_CLIP"
)
LIGHTLY_STUDIO_MODEL_CACHE_DIR: Path = env.path(
    "LIGHTLY_STUDIO_MODEL_CACHE_DIR", Path.home() / ".cache" / "lightly-studio"
)
LIGHTLY_STUDIO_EDGE_MODEL_FILE_PATH: str = env.str("EDGE_MODEL_PATH", "./lightly_model.tar")
LIGHTLY_STUDIO_PROTOCOL: str = env.str("LIGHTLY_STUDIO_PROTOCOL", "http")
LIGHTLY_STUDIO_PORT: int = env.int("LIGHTLY_STUDIO_PORT", 8001)
LIGHTLY_STUDIO_HOST: str = env.str("LIGHTLY_STUDIO_HOST", "localhost")
LIGHTLY_STUDIO_DEBUG: bool = env.bool("LIGHTLY_STUDIO_DEBUG", False)

LIGHTLY_STUDIO_LICENSE_KEY: Optional[str] = env.str("LIGHTLY_STUDIO_LICENSE_KEY", default=None)

LIGHTLY_STUDIO_DATABASE_URL: Optional[str] = env.str("LIGHTLY_STUDIO_DATABASE_URL", default=None)

LIGHTLY_STUDIO_API_URL: Optional[str] = env.str("LIGHTLY_STUDIO_API_URL", default=None)
LIGHTLY_STUDIO_TOKEN: Optional[str] = env.str("LIGHTLY_STUDIO_TOKEN", default=None)

LIGHTLY_STUDIO_REQUEST_TIMING_ENABLED: bool = env.bool(
    "LIGHTLY_STUDIO_REQUEST_TIMING_ENABLED", False
)
LIGHTLY_STUDIO_REQUEST_TIMING_WARNING_MS: int = env.int(
    "LIGHTLY_STUDIO_REQUEST_TIMING_WARNING_MS", 100
)
LIGHTLY_STUDIO_REQUEST_TIMING_ERROR_MS: int = env.int("LIGHTLY_STUDIO_REQUEST_TIMING_ERROR_MS", 200)
LIGHTLY_STUDIO_REQUEST_TIMING_FAIL_ON_ERROR: bool = env.bool(
    "LIGHTLY_STUDIO_REQUEST_TIMING_FAIL_ON_ERROR", False
)
