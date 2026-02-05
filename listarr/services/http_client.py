"""
Shared HTTP client module with connection pooling and retry logic.

All external API calls (Radarr, Sonarr, TMDB) use this shared session
for consistent timeout handling, retry behavior, and connection reuse.
"""

import logging

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

# Constants
DEFAULT_TIMEOUT = 30  # seconds
API_BASE_TMDB = "https://api.themoviedb.org/3"

# Retry strategy for transient errors
# Exponential backoff: 1s, 2s, 4s
retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["HEAD", "GET", "OPTIONS", "POST"],
    raise_on_status=False,
)

# HTTP adapter with connection pooling
adapter = HTTPAdapter(
    max_retries=retry_strategy,
    pool_connections=10,
    pool_maxsize=10,
)

# Module-level shared session
http_session = requests.Session()
http_session.mount("http://", adapter)
http_session.mount("https://", adapter)
http_session.headers.update({"User-Agent": "Listarr/1.0"})

logger.debug("HTTP client initialized with retry strategy (total=3, backoff=1s) and connection pooling (pool_size=10)")


def normalize_url(base_url: str) -> str:
    """
    Normalize base URL by stripping trailing slashes.

    Args:
        base_url: URL to normalize (e.g., "http://localhost:7878/")

    Returns:
        str: URL without trailing slash (e.g., "http://localhost:7878")
    """
    return base_url.rstrip("/")
