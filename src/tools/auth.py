"""
API Key Authentication

Simple API key verification for MCP server.
"""

import os
from fastmcp.server.dependencies import get_http_headers


API_KEY = os.getenv("MCP_API_KEY", "")


def verify_api_key() -> bool:
    """Verify API key from request headers."""
    if not API_KEY:
        return True  # No key = allow (local dev)
    headers = get_http_headers()
    provided = headers.get("x-api-key") or headers.get("authorization", "").replace("Bearer ", "")
    return provided == API_KEY


def require_auth():
    """Raise error if API key is invalid."""
    if not verify_api_key():
        raise ValueError("Invalid or missing API key. Provide X-API-Key header.")
