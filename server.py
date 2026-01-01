"""
SwitchBot Air Conditioner MCP Server

This MCP server provides control over air conditioners through SwitchBot Hub 2.
It exposes tools to control power, temperature, mode, fan speed, and custom commands.

Setup:
1. Add your AC remote to your SwitchBot Hub 2 via the SwitchBot app
2. Get your SwitchBot API token and secret from: https://support.switch-bot.com/hc/en-us/articles/12822710195351
3. Find your AC device ID using the SwitchBot app or API
4. Set environment variables: SWITCHBOT_TOKEN, SWITCHBOT_SECRET, SWITCHBOT_AC_DEVICE_ID
"""

from fastmcp import FastMCP
from fastmcp.server.auth import BearerAuthProvider
import httpx
import hashlib
import hmac
import base64
import time
import uuid
import os
from typing import Literal
from pathlib import Path

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        load_dotenv(env_file)
except ImportError:
    # python-dotenv not installed, will use environment variables
    pass

# Initialize MCP server with Supabase JWT auth
SUPABASE_PROJECT_REF = os.getenv("SUPABASE_PROJECT_REF", "mvoxckiqssdxwfpszsqq")

auth_provider = BearerAuthProvider(
    jwks_uri=f"https://{SUPABASE_PROJECT_REF}.supabase.co/auth/v1/.well-known/jwks.json",
    issuer=f"https://{SUPABASE_PROJECT_REF}.supabase.co/auth/v1",
    audience="authenticated",
)

mcp = FastMCP("SwitchBot AC Controller", auth=auth_provider)

# Configuration - Loaded from .env file or environment variables
SWITCHBOT_TOKEN = os.getenv("SWITCHBOT_TOKEN", "")
SWITCHBOT_SECRET = os.getenv("SWITCHBOT_SECRET", "")
AC_DEVICE_ID = os.getenv("SWITCHBOT_AC_DEVICE_ID", "")

# Debug: Log environment variable status (without exposing values)
import sys
if not SWITCHBOT_TOKEN:
    print("⚠️ WARNING: SWITCHBOT_TOKEN is empty!", file=sys.stderr)
if not SWITCHBOT_SECRET:
    print("⚠️ WARNING: SWITCHBOT_SECRET is empty!", file=sys.stderr)
if not AC_DEVICE_ID:
    print("⚠️ WARNING: SWITCHBOT_AC_DEVICE_ID is empty!", file=sys.stderr)

if SWITCHBOT_TOKEN and SWITCHBOT_SECRET and AC_DEVICE_ID:
    print(f"✅ Environment variables loaded successfully", file=sys.stderr)
    print(f"   Token length: {len(SWITCHBOT_TOKEN)}", file=sys.stderr)
    print(f"   Secret length: {len(SWITCHBOT_SECRET)}", file=sys.stderr)
    print(f"   Device ID: {AC_DEVICE_ID}", file=sys.stderr)

# SwitchBot API base URL
API_BASE = "https://api.switch-bot.com/v1.1"


def generate_sign(token: str, secret: str, nonce: str) -> tuple[str, str]:
    """
    Generate authentication signature for SwitchBot API.
    
    Args:
        token: SwitchBot API token
        secret: SwitchBot API secret
        nonce: Unique nonce (UUID)
    
    Returns:
        tuple: (timestamp in milliseconds, signature)
    """
    t = int(round(time.time() * 1000))
    string_to_sign = f"{token}{t}{nonce}"
    string_to_sign_bytes = bytes(string_to_sign, "utf-8")
    secret_bytes = bytes(secret, "utf-8")
    sign = base64.b64encode(
        hmac.new(secret_bytes, msg=string_to_sign_bytes, digestmod=hashlib.sha256).digest()
    )
    return str(t), str(sign, "utf-8")


async def make_switchbot_request(
    method: str, endpoint: str, data: dict = None
) -> dict:
    """
    Make authenticated request to SwitchBot API.
    
    Args:
        method: HTTP method (GET, POST, etc.)
        endpoint: API endpoint (without base URL)
        data: Request payload for POST requests
    
    Returns:
        dict: API response JSON
    """
    nonce = uuid.uuid4().hex
    t, sign = generate_sign(SWITCHBOT_TOKEN, SWITCHBOT_SECRET, nonce)
    
    headers = {
        "Authorization": SWITCHBOT_TOKEN,
        "sign": sign,
        "nonce": nonce,
        "t": t,
        "Content-Type": "application/json"
    }
    
    url = f"{API_BASE}{endpoint}"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        if method.upper() == "GET":
            response = await client.get(url, headers=headers)
        elif method.upper() == "POST":
            response = await client.post(url, headers=headers, json=data)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
    
    response.raise_for_status()
    return response.json()


@mcp.tool()
async def check_credentials() -> str:
    """
    Check if SwitchBot credentials are configured and valid.
    
    Returns:
        String with credential status
    """
    output = "🔐 Credential Status Check:\n\n"
    
    if not SWITCHBOT_TOKEN:
        output += "❌ SWITCHBOT_TOKEN: Not set\n"
    else:
        output += f"✅ SWITCHBOT_TOKEN: Set ({len(SWITCHBOT_TOKEN)} characters)\n"
    
    if not SWITCHBOT_SECRET:
        output += "❌ SWITCHBOT_SECRET: Not set\n"
    else:
        output += f"✅ SWITCHBOT_SECRET: Set ({len(SWITCHBOT_SECRET)} characters)\n"
    
    if not AC_DEVICE_ID:
        output += "❌ SWITCHBOT_AC_DEVICE_ID: Not set\n"
    else:
        output += f"✅ SWITCHBOT_AC_DEVICE_ID: Set ({AC_DEVICE_ID})\n"
    
    if not (SWITCHBOT_TOKEN and SWITCHBOT_SECRET):
        output += "\n⚠️ Missing credentials! Cannot authenticate with SwitchBot API.\n"
        output += "Please set environment variables in your hosting dashboard."
        return output
    
    # Test authentication
    output += "\n🧪 Testing API Authentication...\n"
    try:
        result = await make_switchbot_request("GET", "/devices")
        if result.get("statusCode") == 100:
            output += "✅ Authentication successful!\n"
            output += "✅ API connection working\n"
        else:
            output += f"❌ Authentication failed: {result.get('message', 'Unknown error')}\n"
            output += "Check that your token and secret are correct.\n"
    except Exception as e:
        output += f"❌ API request failed: {str(e)}\n"
    
    return output


@mcp.tool()
async def get_ac_devices() -> str:
    """
    List all infrared devices (including AC remotes) registered with SwitchBot Hub 2.
    Use this to find your AC device ID if you don't know it yet.
    
    Returns:
        String with list of devices and their IDs
    """
    try:
        result = await make_switchbot_request("GET", "/devices")
        
        if result.get("statusCode") != 100:
            return f"Error: {result.get('message', 'Unknown error')}"
        
        infrared_devices = result.get("body", {}).get("infraredRemoteList", [])
        
        if not infrared_devices:
            return "No infrared devices found. Please add your AC remote to SwitchBot Hub 2 via the app."
        
        output = "Infrared Devices:\n\n"
        for device in infrared_devices:
            device_type = device.get("remoteType", "Unknown")
            device_id = device.get("deviceId", "N/A")
            device_name = device.get("deviceName", "Unnamed")
            hub_id = device.get("hubDeviceId", "N/A")
            
            output += f"Name: {device_name}\n"
            output += f"Type: {device_type}\n"
            output += f"Device ID: {device_id}\n"
            output += f"Hub ID: {hub_id}\n"
            output += "-" * 50 + "\n"
        
        return output
    
    except Exception as e:
        return f"Error retrieving devices: {str(e)}"


@mcp.tool()
async def get_ac_status() -> str:
    """
    Get the current status of the air conditioner.
    
    Note: Status may not be accurate if IR decoding is not enabled or supported.
    The SwitchBot API returns the last known state based on commands sent through the API.
    
    Returns:
        String with current AC status including power, temperature, mode, and fan speed
    """
    try:
        result = await make_switchbot_request("GET", f"/devices/{AC_DEVICE_ID}/status")
        
        if result.get("statusCode") != 100:
            return f"Error: {result.get('message', 'Unknown error')}"
        
        body = result.get("body", {})
        
        power = "ON" if body.get("power") == "on" else "OFF"
        temperature = body.get("temperature", "N/A")
        mode = body.get("mode", "N/A")
        fan_speed = body.get("fanSpeed", "N/A")
        
        output = f"Air Conditioner Status:\n\n"
        output += f"Power: {power}\n"
        output += f"Temperature: {temperature}°C\n"
        output += f"Mode: {mode}\n"
        output += f"Fan Speed: {fan_speed}\n"
        
        return output
    
    except Exception as e:
        return f"Error retrieving AC status: {str(e)}"


@mcp.tool()
async def turn_ac_on(
    temperature: int = 24,
    mode: Literal["auto", "cool", "dry", "fan", "heat"] = "cool",
    fan_speed: Literal["auto", "low", "medium", "high"] = "auto"
) -> str:
    """
    Turn on the air conditioner with specified settings.
    
    Args:
        temperature: Target temperature in Celsius (typically 16-30)
        mode: Operating mode - 'auto', 'cool', 'dry', 'fan', or 'heat'
        fan_speed: Fan speed - 'auto', 'low', 'medium', or 'high'
    
    Returns:
        Status message indicating success or failure
    """
    try:
        # Validate temperature range
        if not 16 <= temperature <= 30:
            return "Error: Temperature must be between 16 and 30 degrees Celsius"
        
        command_data = {
            "command": "setAll",
            "parameter": f"{temperature},{mode},{fan_speed},on",
            "commandType": "command"
        }
        
        result = await make_switchbot_request(
            "POST",
            f"/devices/{AC_DEVICE_ID}/commands",
            command_data
        )
        
        if result.get("statusCode") != 100:
            return f"Error: {result.get('message', 'Unknown error')}"
        
        return f"✓ AC turned ON\n  Temperature: {temperature}°C\n  Mode: {mode}\n  Fan Speed: {fan_speed}"
    
    except Exception as e:
        return f"Error controlling AC: {str(e)}"


@mcp.tool()
async def turn_ac_off() -> str:
    """
    Turn off the air conditioner.
    
    Returns:
        Status message indicating success or failure
    """
    try:
        command_data = {
            "command": "turnOff",
            "parameter": "default",
            "commandType": "command"
        }
        
        result = await make_switchbot_request(
            "POST",
            f"/devices/{AC_DEVICE_ID}/commands",
            command_data
        )
        
        if result.get("statusCode") != 100:
            return f"Error: {result.get('message', 'Unknown error')}"
        
        return "✓ AC turned OFF"
    
    except Exception as e:
        return f"Error controlling AC: {str(e)}"


@mcp.tool()
async def set_ac_temperature(temperature: int) -> str:
    """
    Change the air conditioner temperature while keeping other settings the same.
    
    Note: This requires the AC to be already ON. If the AC is OFF, use turn_ac_on instead.
    
    Args:
        temperature: Target temperature in Celsius (typically 16-30)
    
    Returns:
        Status message indicating success or failure
    """
    try:
        # Validate temperature range
        if not 16 <= temperature <= 30:
            return "Error: Temperature must be between 16 and 30 degrees Celsius"
        
        # First get current status to maintain other settings
        status_result = await make_switchbot_request("GET", f"/devices/{AC_DEVICE_ID}/status")
        
        if status_result.get("statusCode") != 100:
            return f"Error: {status_result.get('message', 'Unable to get current status')}"
        
        body = status_result.get("body", {})
        current_mode = body.get("mode", "cool")
        current_fan = body.get("fanSpeed", "auto")
        
        command_data = {
            "command": "setAll",
            "parameter": f"{temperature},{current_mode},{current_fan},on",
            "commandType": "command"
        }
        
        result = await make_switchbot_request(
            "POST",
            f"/devices/{AC_DEVICE_ID}/commands",
            command_data
        )
        
        if result.get("statusCode") != 100:
            return f"Error: {result.get('message', 'Unknown error')}"
        
        return f"✓ Temperature set to {temperature}°C"
    
    except Exception as e:
        return f"Error setting temperature: {str(e)}"


@mcp.tool()
async def set_ac_mode(
    mode: Literal["auto", "cool", "dry", "fan", "heat"]
) -> str:
    """
    Change the air conditioner operating mode while keeping other settings the same.
    
    Note: This requires the AC to be already ON. If the AC is OFF, use turn_ac_on instead.
    
    Args:
        mode: Operating mode - 'auto', 'cool', 'dry', 'fan', or 'heat'
    
    Returns:
        Status message indicating success or failure
    """
    try:
        # First get current status to maintain other settings
        status_result = await make_switchbot_request("GET", f"/devices/{AC_DEVICE_ID}/status")
        
        if status_result.get("statusCode") != 100:
            return f"Error: {status_result.get('message', 'Unable to get current status')}"
        
        body = status_result.get("body", {})
        current_temp = body.get("temperature", 24)
        current_fan = body.get("fanSpeed", "auto")
        
        command_data = {
            "command": "setAll",
            "parameter": f"{current_temp},{mode},{current_fan},on",
            "commandType": "command"
        }
        
        result = await make_switchbot_request(
            "POST",
            f"/devices/{AC_DEVICE_ID}/commands",
            command_data
        )
        
        if result.get("statusCode") != 100:
            return f"Error: {result.get('message', 'Unknown error')}"
        
        return f"✓ Mode set to {mode}"
    
    except Exception as e:
        return f"Error setting mode: {str(e)}"


@mcp.tool()
async def set_ac_fan_speed(
    fan_speed: Literal["auto", "low", "medium", "high"]
) -> str:
    """
    Change the air conditioner fan speed while keeping other settings the same.
    
    Note: This requires the AC to be already ON. If the AC is OFF, use turn_ac_on instead.
    
    Args:
        fan_speed: Fan speed - 'auto', 'low', 'medium', or 'high'
    
    Returns:
        Status message indicating success or failure
    """
    try:
        # First get current status to maintain other settings
        status_result = await make_switchbot_request("GET", f"/devices/{AC_DEVICE_ID}/status")
        
        if status_result.get("statusCode") != 100:
            return f"Error: {status_result.get('message', 'Unable to get current status')}"
        
        body = status_result.get("body", {})
        current_temp = body.get("temperature", 24)
        current_mode = body.get("mode", "cool")
        
        command_data = {
            "command": "setAll",
            "parameter": f"{current_temp},{current_mode},{fan_speed},on",
            "commandType": "command"
        }
        
        result = await make_switchbot_request(
            "POST",
            f"/devices/{AC_DEVICE_ID}/commands",
            command_data
        )
        
        if result.get("statusCode") != 100:
            return f"Error: {result.get('message', 'Unknown error')}"
        
        return f"✓ Fan speed set to {fan_speed}"
    
    except Exception as e:
        return f"Error setting fan speed: {str(e)}"


@mcp.tool()
async def set_ac_all_settings(
    power: Literal["on", "off"],
    temperature: int = 24,
    mode: Literal["auto", "cool", "dry", "fan", "heat"] = "cool",
    fan_speed: Literal["auto", "low", "medium", "high"] = "auto"
) -> str:
    """
    Set all air conditioner settings at once (power, temperature, mode, and fan speed).
    
    This is the most comprehensive control function that allows you to specify all parameters.
    
    Args:
        power: Power state - 'on' or 'off'
        temperature: Target temperature in Celsius (16-30, only used when power is 'on')
        mode: Operating mode - 'auto', 'cool', 'dry', 'fan', or 'heat'
        fan_speed: Fan speed - 'auto', 'low', 'medium', or 'high'
    
    Returns:
        Status message indicating success or failure
    """
    try:
        if power == "off":
            return await turn_ac_off()
        
        # Validate temperature range
        if not 16 <= temperature <= 30:
            return "Error: Temperature must be between 16 and 30 degrees Celsius"
        
        command_data = {
            "command": "setAll",
            "parameter": f"{temperature},{mode},{fan_speed},{power}",
            "commandType": "command"
        }
        
        result = await make_switchbot_request(
            "POST",
            f"/devices/{AC_DEVICE_ID}/commands",
            command_data
        )
        
        if result.get("statusCode") != 100:
            return f"Error: {result.get('message', 'Unknown error')}"
        
        status = "ON" if power == "on" else "OFF"
        return f"✓ AC settings updated\n  Power: {status}\n  Temperature: {temperature}°C\n  Mode: {mode}\n  Fan Speed: {fan_speed}"
    
    except Exception as e:
        return f"Error controlling AC: {str(e)}"


@mcp.tool()
async def send_custom_ac_command(
    command: str,
    parameter: str = "default"
) -> str:
    """
    Send a custom/raw command to the air conditioner.
    
    This allows you to send commands that aren't available in the standard UI.
    Useful for accessing additional buttons like swing, timer, sleep mode, turbo, etc.
    
    Common commands for AC devices:
    - turnOn: Turn on AC
    - turnOff: Turn off AC
    - setAll: Set all parameters (parameter format: "temperature,mode,fanspeed,power")
    - swing: Toggle swing mode
    - timer: Set timer (parameter varies by model)
    - sleep: Activate sleep/night mode
    - turbo: Activate turbo/powerful mode
    - brightnessUp: Increase display brightness
    - brightnessDown: Decrease display brightness
    
    Note: Available commands depend on your AC model and the template used in SwitchBot.
    Some commands may not work if not supported by your specific AC unit.
    
    Args:
        command: The command name (e.g., "swing", "timer", "sleep", "turbo")
        parameter: Command parameter (default: "default"). Format varies by command.
    
    Returns:
        Status message indicating success or failure
    
    Examples:
        - send_custom_ac_command("swing", "default") - Toggle swing mode
        - send_custom_ac_command("sleep", "default") - Activate sleep mode
        - send_custom_ac_command("turbo", "default") - Activate turbo mode
    """
    try:
        command_data = {
            "command": command,
            "parameter": parameter,
            "commandType": "command"
        }
        
        result = await make_switchbot_request(
            "POST",
            f"/devices/{AC_DEVICE_ID}/commands",
            command_data
        )
        
        if result.get("statusCode") != 100:
            return f"Error: {result.get('message', 'Unknown error')}\n  Command: {command}\n  Parameter: {parameter}"
        
        return f"✓ Custom command sent successfully\n  Command: {command}\n  Parameter: {parameter}"
    
    except Exception as e:
        return f"Error sending custom command: {str(e)}"


@mcp.tool()
async def list_common_ac_commands() -> str:
    """
    List common AC commands that might be available beyond the standard controls.
    
    Returns helpful information about additional commands you can try with send_custom_ac_command.
    
    Returns:
        String with list of common AC commands and their descriptions
    """
    output = "🎮 Common AC Commands Beyond Standard Controls:\n\n"
    output += "Standard Commands (already available as dedicated tools):\n"
    output += "  • turnOn - Power on the AC\n"
    output += "  • turnOff - Power off the AC\n"
    output += "  • setAll - Set all parameters (temp,mode,fan,power)\n\n"
    
    output += "Additional Commands (use with send_custom_ac_command):\n"
    output += "  • swing - Toggle vertical air swing/oscillation\n"
    output += "  • swingHorizontal - Toggle horizontal air swing (some models)\n"
    output += "  • timer - Set timer (parameter varies by model)\n"
    output += "  • sleep - Activate sleep/night mode for quiet operation\n"
    output += "  • turbo - Activate turbo/powerful/max cooling mode\n"
    output += "  • economy - Activate economy/energy-saving mode\n"
    output += "  • quiet - Activate quiet/silent mode\n"
    output += "  • light - Toggle display light on/off\n"
    output += "  • brightnessUp - Increase display brightness\n"
    output += "  • brightnessDown - Decrease display brightness\n"
    output += "  • ionizer - Toggle ionizer/air purifier (if equipped)\n"
    output += "  • health - Activate health/fresh air mode (some models)\n\n"
    
    output += "⚠️ Important Notes:\n"
    output += "  • Not all commands work with all AC models\n"
    output += "  • Available commands depend on your AC template in SwitchBot\n"
    output += "  • If a command doesn't work, your AC may not support it\n"
    output += "  • Commands are case-sensitive (use exact capitalization)\n\n"
    
    output += "💡 How to Use:\n"
    output += '  Ask: "Send custom AC command swing"\n'
    output += '  Or: "Activate turbo mode on AC"\n'
    output += '  Or: "Toggle AC swing mode"\n\n'
    
    output += "🔍 To Discover More Commands:\n"
    output += "  • Check your AC's physical remote buttons\n"
    output += "  • Test button names that match your remote's functions\n"
    output += "  • Look at SwitchBot's AC template for your brand\n"
    
    return output


@mcp.tool()
async def get_room_temperature() -> str:
    """
    Get the current room temperature and humidity from the SwitchBot Hub 2.
    
    The Hub 2 has built-in temperature and humidity sensors that measure
    the ambient conditions in the room where it's located.
    
    Returns:
        String with current temperature (°C) and humidity (%)
    """
    try:
        # Get the Hub device ID from the infrared device list
        devices_result = await make_switchbot_request("GET", "/devices")
        
        if devices_result.get("statusCode") != 100:
            return f"Error: {devices_result.get('message', 'Unable to get devices')}"
        
        # Find the Hub ID from our AC device
        infrared_devices = devices_result.get("body", {}).get("infraredRemoteList", [])
        hub_id = None
        
        for device in infrared_devices:
            if device.get("deviceId") == AC_DEVICE_ID:
                hub_id = device.get("hubDeviceId")
                break
        
        if not hub_id:
            return "Error: Could not find Hub 2 device ID. Make sure AC is configured."
        
        # Get Hub 2 status (includes temperature and humidity)
        hub_result = await make_switchbot_request("GET", f"/devices/{hub_id}/status")
        
        if hub_result.get("statusCode") != 100:
            return f"Error: {hub_result.get('message', 'Unable to get Hub status')}"
        
        body = hub_result.get("body", {})
        temperature = body.get("temperature")
        humidity = body.get("humidity")
        
        if temperature is None or humidity is None:
            return "⚠️ Hub 2 sensor data not available. Make sure your Hub 2 model has built-in sensors."
        
        output = "🌡️ Room Conditions (from Hub 2):\n\n"
        output += f"Temperature: {temperature}°C\n"
        output += f"Humidity: {humidity}%\n"
        
        # Add comfort assessment
        if temperature < 18:
            output += "\n❄️ It's quite cold in the room"
        elif temperature < 22:
            output += "\n🌤️ Room temperature is cool"
        elif temperature < 26:
            output += "\n😊 Room temperature is comfortable"
        elif temperature < 30:
            output += "\n🔥 Room is getting warm"
        else:
            output += "\n🥵 Room is very hot!"
        
        return output
    
    except Exception as e:
        return f"Error getting room temperature: {str(e)}"


if __name__ == "__main__":
    # Run the MCP server
    mcp.run()

