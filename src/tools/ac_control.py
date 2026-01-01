"""
AC Control Tools

MCP tools for controlling the air conditioner.
"""

from typing import Literal
from fastmcp import FastMCP
from ..switchbot import ACCommands
from .auth import require_auth


def register_ac_control_tools(mcp: FastMCP, ac: ACCommands):
    """Register AC control tools with the MCP server."""

    @mcp.tool()
    async def turn_ac_on(
        temperature: int = 24,
        mode: Literal["auto", "cool", "dry", "fan", "heat"] = "cool",
        fan_speed: Literal["auto", "low", "medium", "high"] = "auto",
    ) -> str:
        """Turn on the AC with specified settings."""
        require_auth()
        if not 16 <= temperature <= 30:
            return "Error: Temperature must be between 16 and 30°C"

        result = await ac.set_all("on", temperature, mode, fan_speed)
        if result.get("statusCode") != 100:
            return f"Error: {result.get('message', 'Unknown error')}"

        return f"✓ AC turned ON\n  Temperature: {temperature}°C\n  Mode: {mode}\n  Fan Speed: {fan_speed}"

    @mcp.tool()
    async def turn_ac_off() -> str:
        """Turn off the AC."""
        require_auth()
        result = await ac.turn_off()
        if result.get("statusCode") != 100:
            return f"Error: {result.get('message', 'Unknown error')}"
        return "✓ AC turned OFF"

    @mcp.tool()
    async def set_ac_temperature(temperature: int) -> str:
        """Change AC temperature (AC must be on)."""
        require_auth()
        if not 16 <= temperature <= 30:
            return "Error: Temperature must be between 16 and 30°C"

        status = await ac.get_status()
        mode = status.get("mode", "cool")
        fan = status.get("fanSpeed", "auto")

        result = await ac.set_all("on", temperature, mode, fan)
        if result.get("statusCode") != 100:
            return f"Error: {result.get('message', 'Unknown error')}"
        return f"✓ Temperature set to {temperature}°C"

    @mcp.tool()
    async def set_ac_mode(mode: Literal["auto", "cool", "dry", "fan", "heat"]) -> str:
        """Change AC mode (AC must be on)."""
        require_auth()
        status = await ac.get_status()
        temp = status.get("temperature", 24)
        fan = status.get("fanSpeed", "auto")

        result = await ac.set_all("on", temp, mode, fan)
        if result.get("statusCode") != 100:
            return f"Error: {result.get('message', 'Unknown error')}"
        return f"✓ Mode set to {mode}"

    @mcp.tool()
    async def set_ac_fan_speed(fan_speed: Literal["auto", "low", "medium", "high"]) -> str:
        """Change AC fan speed (AC must be on)."""
        require_auth()
        status = await ac.get_status()
        temp = status.get("temperature", 24)
        mode = status.get("mode", "cool")

        result = await ac.set_all("on", temp, mode, fan_speed)
        if result.get("statusCode") != 100:
            return f"Error: {result.get('message', 'Unknown error')}"
        return f"✓ Fan speed set to {fan_speed}"

    @mcp.tool()
    async def set_ac_all_settings(
        power: Literal["on", "off"],
        temperature: int = 24,
        mode: Literal["auto", "cool", "dry", "fan", "heat"] = "cool",
        fan_speed: Literal["auto", "low", "medium", "high"] = "auto",
    ) -> str:
        """Set all AC settings at once."""
        require_auth()
        if power == "on" and not 16 <= temperature <= 30:
            return "Error: Temperature must be between 16 and 30°C"

        result = await ac.set_all(power, temperature, mode, fan_speed)
        if result.get("statusCode") != 100:
            return f"Error: {result.get('message', 'Unknown error')}"

        if power == "off":
            return "✓ AC turned OFF"
        return f"✓ AC settings updated\n  Power: ON\n  Temperature: {temperature}°C\n  Mode: {mode}\n  Fan Speed: {fan_speed}"

    @mcp.tool()
    async def send_custom_ac_command(command: str, parameter: str = "default") -> str:
        """Send custom command (swing, turbo, sleep, etc.)."""
        require_auth()
        result = await ac.send_custom(command, parameter)
        if result.get("statusCode") != 100:
            return f"Error: {result.get('message', 'Unknown error')}\n  Command: {command}"
        return f"✓ Custom command sent\n  Command: {command}\n  Parameter: {parameter}"
