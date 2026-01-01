"""
Supabase Logging

Log automation decisions and fetch history.
"""

import httpx


async def log_to_supabase(url: str, key: str, data: dict) -> bool:
    """Log decision to Supabase."""
    if not url or not key:
        return False

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{url}/rest/v1/ac_automation_logs",
                json=data,
                headers={
                    "apikey": key,
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal",
                },
            )
            return response.status_code == 201
    except Exception:
        return False


async def get_history(url: str, key: str, limit: int = 10) -> list:
    """Get recent decisions from Supabase."""
    if not url or not key:
        return []

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{url}/rest/v1/ac_automation_logs",
                params={
                    "select": "*",
                    "order": "created_at.desc",
                    "limit": str(limit),
                },
                headers={
                    "apikey": key,
                    "Authorization": f"Bearer {key}",
                },
            )
            if response.status_code == 200:
                return response.json()
            return []
    except Exception:
        return []
