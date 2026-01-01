"""
Discovery Tools

MCP tools for discovering devices and checking credentials.
"""

from fastmcp import FastMCP
from ..switchbot import SwitchBotClient
from .auth import require_auth


def register_discovery_tools(mcp: FastMCP, client: SwitchBotClient, device_id: str):
    """Register discovery tools with the MCP server."""

    @mcp.tool()
    async def check_credentials() -> str:
        """Check if SwitchBot credentials are configured and valid."""
        require_auth()
        output = "🔐 Credential Status Check:\n\n"

        if not client.token:
            output += "❌ SWITCHBOT_TOKEN: Not set\n"
        else:
            output += f"✅ SWITCHBOT_TOKEN: Set ({len(client.token)} chars)\n"

        if not client.secret:
            output += "❌ SWITCHBOT_SECRET: Not set\n"
        else:
            output += f"✅ SWITCHBOT_SECRET: Set ({len(client.secret)} chars)\n"

        if not device_id:
            output += "❌ SWITCHBOT_AC_DEVICE_ID: Not set\n"
        else:
            output += f"✅ SWITCHBOT_AC_DEVICE_ID: {device_id}\n"

        if not (client.token and client.secret):
            output += "\n⚠️ Missing credentials!"
            return output

        output += "\n🧪 Testing API Authentication...\n"
        try:
            result = await client.get_devices()
            if result.get("statusCode") == 100:
                output += "✅ Authentication successful!\n"
            else:
                output += f"❌ Authentication failed: {result.get('message')}\n"
        except Exception as e:
            output += f"❌ API request failed: {e}\n"

        return output

    @mcp.tool()
    async def get_ac_devices() -> str:
        """List all infrared devices (to find your AC device ID)."""
        require_auth()
        try:
            result = await client.get_devices()
            if result.get("statusCode") != 100:
                return f"Error: {result.get('message', 'Unknown error')}"

            devices = result.get("body", {}).get("infraredRemoteList", [])
            if not devices:
                return "No infrared devices found. Add your AC remote via the SwitchBot app."

            output = "Infrared Devices:\n\n"
            for dev in devices:
                output += f"Name: {dev.get('deviceName', 'Unnamed')}\n"
                output += f"Type: {dev.get('remoteType', 'Unknown')}\n"
                output += f"Device ID: {dev.get('deviceId', 'N/A')}\n"
                output += f"Hub ID: {dev.get('hubDeviceId', 'N/A')}\n"
                output += "-" * 40 + "\n"

            return output
        except Exception as e:
            return f"Error retrieving devices: {e}"

    @mcp.tool()
    async def list_common_ac_commands() -> str:
        """List common AC commands for send_custom_ac_command."""
        require_auth()
        return """🎮 Common AC Commands:

Standard:
  • turnOn / turnOff - Power control
  • setAll - Set all parameters

Custom (use with send_custom_ac_command):
  • swing - Toggle vertical swing
  • swingHorizontal - Toggle horizontal swing
  • timer - Set timer
  • sleep - Activate sleep mode
  • turbo - Activate turbo mode
  • economy - Energy saving mode
  • quiet - Silent mode
  • light - Toggle display light

⚠️ Not all commands work with all AC models."""
