"""
Minimal API key auth. Every client (Reinvention Edit, or any future
umbrella-company app) authenticates with a header:

    X-API-Key: <key>

This is intentionally simple for v1 — good enough to keep the API from
being wide open, without the overhead of a full auth system. Rotate keys
by updating the API_KEYS environment variable on your host.
"""
from fastapi import Header, HTTPException, status

from app.core.config import settings


async def require_api_key(x_api_key: str = Header(default=None)) -> str:
    if not x_api_key or x_api_key not in settings.valid_api_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API key. Send it as the X-API-Key header.",
        )
    return x_api_key
