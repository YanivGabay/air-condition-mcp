"""
SwitchBot API Client

Handles authentication and requests to the SwitchBot API.
"""

import hashlib
import hmac
import base64
import time
import uuid
import httpx


API_BASE = "https://api.switch-bot.com/v1.1"


class SwitchBotClient:
    """Async client for SwitchBot API."""

    def __init__(self, token: str, secret: str):
        self.token = token
        self.secret = secret

    def _generate_sign(self, nonce: str) -> tuple[str, str]:
        """Generate authentication signature."""
        t = int(round(time.time() * 1000))
        string_to_sign = f"{self.token}{t}{nonce}"
        sign = base64.b64encode(
            hmac.new(
                self.secret.encode("utf-8"),
                msg=string_to_sign.encode("utf-8"),
                digestmod=hashlib.sha256,
            ).digest()
        )
        return str(t), sign.decode("utf-8")

    def _get_headers(self) -> dict:
        """Get authenticated headers for API request."""
        nonce = uuid.uuid4().hex
        t, sign = self._generate_sign(nonce)
        return {
            "Authorization": self.token,
            "sign": sign,
            "nonce": nonce,
            "t": t,
            "Content-Type": "application/json",
        }

    async def request(self, method: str, endpoint: str, data: dict = None) -> dict:
        """Make authenticated request to SwitchBot API."""
        url = f"{API_BASE}{endpoint}"
        headers = self._get_headers()

        async with httpx.AsyncClient(timeout=30.0) as client:
            if method.upper() == "GET":
                response = await client.get(url, headers=headers)
            elif method.upper() == "POST":
                response = await client.post(url, headers=headers, json=data)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

        response.raise_for_status()
        return response.json()

    async def get_devices(self) -> dict:
        """Get all devices including infrared remotes."""
        return await self.request("GET", "/devices")

    async def get_device_status(self, device_id: str) -> dict:
        """Get status of a specific device."""
        return await self.request("GET", f"/devices/{device_id}/status")

    async def send_command(self, device_id: str, command: str, parameter: str = "default") -> dict:
        """Send command to a device."""
        data = {
            "command": command,
            "parameter": parameter,
            "commandType": "command",
        }
        return await self.request("POST", f"/devices/{device_id}/commands", data)
