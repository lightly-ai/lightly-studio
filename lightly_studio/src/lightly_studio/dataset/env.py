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

# Fixed source used by the MCAP processing-boundary proof of concept. Keeping the
# source server-configured avoids exposing an arbitrary file or URL reader endpoint.
LIGHTLY_STUDIO_MCAP_POC_SOURCE: Optional[str] = env.str(
    "LIGHTLY_STUDIO_MCAP_POC_SOURCE", default=None
)

# Anonymous usage tracking. Covers the Python package and the GUI, which reads the flag back from
# the API. See lightly_studio/analytics/tracking.py.
LIGHTLY_STUDIO_ANALYTICS_ENABLED: bool = env.bool("LIGHTLY_STUDIO_ANALYTICS_ENABLED", True)
# The same project the webapp reports to, so backend and browser events land together. PostHog
# project API keys are write-only and ship inside every client: this one is already in the webapp
# bundle of every published wheel, so keeping it out of the source buys nothing. Set the variable
# to point a build elsewhere, or to "" to disable tracking without touching the flag above.
LIGHTLY_STUDIO_POSTHOG_KEY: str = env.str(
    "LIGHTLY_STUDIO_POSTHOG_KEY", "phc_LB62TVP2O3S2goH4KASascsXRT14H7zfxHVfo7d2cLV"
)
# The EU instance, matching PUBLIC_POSTHOG_HOST in lightly_studio_view/.env. The two packages read
# their configuration through different systems, so the value is written once on each side. Not an
# environment variable: the key above is the only part worth pointing elsewhere.
LIGHTLY_STUDIO_POSTHOG_HOST: str = "https://eu.i.posthog.com"

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
