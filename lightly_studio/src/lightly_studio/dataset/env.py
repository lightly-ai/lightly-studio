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
# The same project the webapp reports to, so backend and browser events land together. PostHog
# project API keys are write-only and ship inside every client: this one is already in the webapp
# bundle of every published wheel, so keeping it out of the source buys nothing. Set the variable
# to point a build elsewhere, or to "" to disable tracking without touching the flag above.
LIGHTLY_STUDIO_POSTHOG_KEY: str = env.str(
    "LIGHTLY_STUDIO_POSTHOG_KEY", "phc_LB62TVP2O3S2goH4KASascsXRT14H7zfxHVfo7d2cLV"
)
# The EU instance, matching PUBLIC_POSTHOG_HOST in lightly_studio_view/.env. The two packages read
# their configuration through different systems, so the value is written once on each side.
LIGHTLY_STUDIO_POSTHOG_HOST: str = env.str(
    "LIGHTLY_STUDIO_POSTHOG_HOST", "https://eu.i.posthog.com"
)

# Number of concurrent reads issued against remote (cloud) storage during import. Sized for
# request latency rather than CPU count: a remote read spends nearly all its time waiting, so
# more can be in flight than there are cores. Local paths keep the CPU-derived worker count
# instead, because extra threads only add contention on a local disk.
#
# Do not raise this much higher without measuring. All fsspec cloud backends funnel their I/O
# through one shared asyncio event loop, so past a few tens of readers that loop, not the
# network, is the limit: throughput measurably degrades and very high values are slower than
# reading serially.
LIGHTLY_STUDIO_IO_CONCURRENCY: int = env.int("LIGHTLY_STUDIO_IO_CONCURRENCY", 16)
# Read-ahead block size for partial reads from remote storage. The s3fs default is 50 MiB, which
# makes a header-only read (e.g. reading image dimensions) fetch the whole object; 256 KiB keeps
# such a read to a single small request.
LIGHTLY_STUDIO_REMOTE_BLOCK_SIZE: int = env.int("LIGHTLY_STUDIO_REMOTE_BLOCK_SIZE", 256 * 1024)
# Size of the underlying HTTP connection pool for S3. Must be at least
# LIGHTLY_STUDIO_IO_CONCURRENCY, or concurrent readers queue behind the pool instead of running
# in parallel. 0 means "derive from LIGHTLY_STUDIO_IO_CONCURRENCY"; botocore's own default is 10.
LIGHTLY_STUDIO_S3_MAX_POOL_CONNECTIONS: int = env.int("LIGHTLY_STUDIO_S3_MAX_POOL_CONNECTIONS", 0)

LIGHTLY_STUDIO_REQUEST_TIMING_ENABLED: bool = env.bool(
    "LIGHTLY_STUDIO_REQUEST_TIMING_ENABLED", False
)
LIGHTLY_STUDIO_REQUEST_TIMING_ERROR_MS: int = env.int("LIGHTLY_STUDIO_REQUEST_TIMING_ERROR_MS", 200)
LIGHTLY_STUDIO_REQUEST_TIMING_FAIL_ON_ERROR: bool = env.bool(
    "LIGHTLY_STUDIO_REQUEST_TIMING_FAIL_ON_ERROR", False
)
