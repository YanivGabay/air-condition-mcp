"""
MCP Client Utilities

Connect to MCP server and call tools.
"""

from fastmcp import Client


def create_mcp_client(url: str, api_key: str) -> Client:
    """Create MCP client with API key auth."""
    if not api_key:
        raise RuntimeError("MCP_API_KEY not set")

    config = {
        "mcpServers": {
            "ac": {
                "transport": "http",
                "url": url,
                "headers": {"X-API-Key": api_key},
            }
        }
    }
    return Client(config)


async def get_room_conditions(client: Client) -> dict:
    """Get room temperature and humidity."""
    try:
        result = await client.call_tool("get_room_temperature", {})
        text = result.data if hasattr(result, "data") else str(result)

        temp_match = text.find("Temperature:")
        humid_match = text.find("Humidity:")

        if temp_match != -1 and humid_match != -1:
            temp_line = text[temp_match:].split("\n")[0]
            humid_line = text[humid_match:].split("\n")[0]
            temperature = float(temp_line.split(":")[1].replace("°C", "").strip())
            humidity = float(humid_line.split(":")[1].replace("%", "").strip())
            return {"temperature": temperature, "humidity": humidity}

        return {"error": "Could not parse room conditions"}
    except Exception as e:
        return {"error": str(e)}


async def get_ac_status(client: Client) -> dict:
    """Get current AC status."""
    try:
        result = await client.call_tool("get_ac_status", {})
        text = result.data if hasattr(result, "data") else str(result)

        status = {"power": "off", "temperature": None, "mode": None, "fan_speed": None}

        for line in text.split("\n"):
            if "Power:" in line:
                status["power"] = "on" if "ON" in line.upper() else "off"
            elif "Temperature:" in line:
                try:
                    status["temperature"] = int(line.split(":")[1].replace("°C", "").strip())
                except ValueError:
                    pass
            elif "Mode:" in line:
                status["mode"] = line.split(":")[1].strip().lower()
            elif "Fan Speed:" in line:
                status["fan_speed"] = line.split(":")[1].strip().lower()

        return status
    except Exception as e:
        return {"error": str(e)}


async def execute_action(client: Client, decision: dict, config: dict) -> dict:
    """Execute AC action based on AI decision."""
    action = decision.get("action", "none")

    if action == "none":
        return {"executed": False, "reason": "No action needed"}

    try:
        default_mode = config.get("rules", {}).get("preferred_mode", "cool")

        if action == "turn_off":
            result = await client.call_tool("turn_ac_off", {})
        elif action in ("turn_on", "adjust_temp", "change_mode"):
            result = await client.call_tool(
                "set_ac_all_settings",
                {
                    "power": "off" if action == "turn_off" else "on",
                    "temperature": decision.get("temperature", 22),
                    "mode": decision.get("mode", default_mode),
                    "fan_speed": decision.get("fan_speed", "auto"),
                },
            )
        else:
            return {"executed": False, "reason": f"Unknown action: {action}"}

        result_str = result.data if hasattr(result, "data") else str(result)

        if "✓" in result_str or "success" in result_str.lower():
            return {"executed": True, "result": result_str}
        return {"executed": False, "reason": result_str}

    except Exception as e:
        return {"executed": False, "reason": str(e)}
