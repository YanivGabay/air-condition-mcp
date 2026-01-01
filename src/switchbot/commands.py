"""
AC Commands

High-level commands for controlling air conditioners via SwitchBot.
"""

from typing import Literal
from .client import SwitchBotClient


class ACCommands:
    """AC-specific commands using SwitchBot client."""

    def __init__(self, client: SwitchBotClient, device_id: str):
        self.client = client
        self.device_id = device_id

    async def get_status(self) -> dict:
        """Get AC status (power, temp, mode, fan)."""
        result = await self.client.get_device_status(self.device_id)
        if result.get("statusCode") != 100:
            raise Exception(result.get("message", "Failed to get status"))
        return result.get("body", {})

    async def turn_off(self) -> dict:
        """Turn off the AC."""
        return await self.client.send_command(self.device_id, "turnOff")

    async def set_all(
        self,
        power: Literal["on", "off"],
        temperature: int,
        mode: Literal["auto", "cool", "dry", "fan", "heat"],
        fan_speed: Literal["auto", "low", "medium", "high"],
    ) -> dict:
        """Set all AC parameters at once."""
        if power == "off":
            return await self.turn_off()

        parameter = f"{temperature},{mode},{fan_speed},{power}"
        return await self.client.send_command(self.device_id, "setAll", parameter)

    async def send_custom(self, command: str, parameter: str = "default") -> dict:
        """Send custom command (swing, turbo, sleep, etc.)."""
        return await self.client.send_command(self.device_id, command, parameter)

    async def get_hub_temperature(self) -> dict | None:
        """Get room temperature from Hub 2 sensor."""
        # First find the hub ID from the device list
        devices = await self.client.get_devices()
        if devices.get("statusCode") != 100:
            return None

        infrared_list = devices.get("body", {}).get("infraredRemoteList", [])
        hub_id = None
        for device in infrared_list:
            if device.get("deviceId") == self.device_id:
                hub_id = device.get("hubDeviceId")
                break

        if not hub_id:
            return None

        hub_status = await self.client.get_device_status(hub_id)
        if hub_status.get("statusCode") != 100:
            return None

        body = hub_status.get("body", {})
        return {
            "temperature": body.get("temperature"),
            "humidity": body.get("humidity"),
        }
