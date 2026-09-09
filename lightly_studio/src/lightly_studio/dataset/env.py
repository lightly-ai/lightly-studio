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
LIGHTLY_STUDIO_PROTOCOL: str = env.str("LIGHTLY_STUDIO_PROTOCOL", "http")
LIGHTLY_STUDIO_PORT: int = env.int("LIGHTLY_STUDIO_PORT", 8001)
LIGHTLY_STUDIO_HOST: str = env.str("LIGHTLY_STUDIO_HOST", "localhost")
LIGHTLY_STUDIO_DEBUG: bool = env.bool("LIGHTLY_STUDIO_DEBUG", False)

LIGHTLY_STUDIO_DATABASE_URL: Optional[str] = env.str("LIGHTLY_STUDIO_DATABASE_URL", default=None)

LIGHTLY_STUDIO_API_URL: Optional[str] = env.str("LIGHTLY_STUDIO_API_URL", default=None)
LIGHTLY_STUDIO_TOKEN: Optional[str] = env.str("LIGHTLY_STUDIO_TOKEN", default=None)
LIGHTLY_STUDIO_API_KEY: Optional[str] = env.str("LIGHTLY_STUDIO_API_KEY", default=None)

# Anonymous usage tracking. Covers the Python package and the GUI, which reads the flag back from
# the API. See lightly_studio/analytics/tracking.py.
LIGHTLY_STUDIO_ANALYTICS_ENABLED: bool = env.bool("LIGHTLY_STUDIO_ANALYTICS_ENABLED", True)
# Overrides the project to report against. Unset or empty, it follows the cohort of the
# installation, see lightly_studio/analytics/posthog_project.py.
LIGHTLY_STUDIO_POSTHOG_KEY: Optional[str] = env.str("LIGHTLY_STUDIO_POSTHOG_KEY", default=None)
# The EU instance. The GUI reads this back from the API rather than carrying its own copy. Not an
# environment variable: the key above is the only part worth pointing elsewhere.
LIGHTLY_STUDIO_POSTHOG_HOST: str = "https://eu.i.posthog.com"
# Marks this machine as a Lightly dev or staff machine, so internal usage can be filtered out of
# the product metrics. See lightly_studio/analytics/cohort.py for the alternative marker file,
# which survives recreating the virtualenv.
LIGHTLY_STUDIO_INTERNAL: bool = env.bool("LIGHTLY_STUDIO_INTERNAL", False)

LIGHTLY_STUDIO_REMOTE_IMAGE_PROBE_WORKERS: int = max(
    1, env.int("LIGHTLY_STUDIO_REMOTE_IMAGE_PROBE_WORKERS", 32)
)

LIGHTLY_STUDIO_REQUEST_TIMING_ENABLED: bool = env.bool(
    "LIGHTLY_STUDIO_REQUEST_TIMING_ENABLED", False
)
LIGHTLY_STUDIO_REQUEST_TIMING_ERROR_MS: int = env.int("LIGHTLY_STUDIO_REQUEST_TIMING_ERROR_MS", 200)
LIGHTLY_STUDIO_REQUEST_TIMING_FAIL_ON_ERROR: bool = env.bool(
    "LIGHTLY_STUDIO_REQUEST_TIMING_FAIL_ON_ERROR", False
)
