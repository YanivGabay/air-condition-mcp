"""
Status Tools

MCP tools for checking AC and room status.
"""

from fastmcp import FastMCP
from ..switchbot import ACCommands
from .auth import require_auth


def register_status_tools(mcp: FastMCP, ac: ACCommands):
    """Register status tools with the MCP server."""

    @mcp.tool()
    async def get_ac_status() -> str:
        """Get current AC status (power, temp, mode, fan)."""
        require_auth()
        try:
            status = await ac.get_status()
            power = "ON" if status.get("power") == "on" else "OFF"
            temp = status.get("temperature", "N/A")
            mode = status.get("mode", "N/A")
            fan = status.get("fanSpeed", "N/A")

            return f"Air Conditioner Status:\n\nPower: {power}\nTemperature: {temp}°C\nMode: {mode}\nFan Speed: {fan}"
        except Exception as e:
            return f"Error retrieving AC status: {e}"

    @mcp.tool()
    async def get_room_temperature() -> str:
        """Get room temperature and humidity from Hub 2."""
        require_auth()
        try:
            data = await ac.get_hub_temperature()
            if not data:
                return "⚠️ Hub 2 sensor data not available"

            temp = data.get("temperature")
            humidity = data.get("humidity")

            output = f"🌡️ Room Conditions (from Hub 2):\n\nTemperature: {temp}°C\nHumidity: {humidity}%"

            if temp is not None:
                if temp < 18:
                    output += "\n\n❄️ It's quite cold"
                elif temp < 22:
                    output += "\n\n🌤️ Cool"
                elif temp < 26:
                    output += "\n\n😊 Comfortable"
                elif temp < 30:
                    output += "\n\n🔥 Getting warm"
                else:
                    output += "\n\n🥵 Very hot!"

            return output
        except Exception as e:
            return f"Error getting room temperature: {e}"
