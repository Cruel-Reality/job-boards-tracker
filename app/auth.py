"""API-key authentication for mutating endpoints.

A single shared secret in the API_KEY env var guards write and ingest routes;
read routes stay public so the deployed demo is browsable without a key. Attach
require_api_key as a FastAPI dependency on the routes that need it.
"""

import os
import secrets

from fastapi import Header, HTTPException, status


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Allow the request only if X-API-Key matches the configured API_KEY.

    Read API_KEY per-request (not at import) so tests and .env loading don't
    depend on import order.
    """
    expected = os.getenv("API_KEY")

    # Fail closed: with no key configured, refuse writes rather than allow all.
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Server auth is not configured (API_KEY unset).",
        )

    # compare_digest is constant-time, so a wrong key can't be guessed by timing
    # how long the comparison takes.
    if not x_api_key or not secrets.compare_digest(x_api_key, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
        )
