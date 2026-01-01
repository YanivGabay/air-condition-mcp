#!/usr/bin/env python3
"""
AC Night Automation Scheduler

This script runs every hour during night hours to automatically adjust
the air conditioner based on room conditions, weather, and historical data.

Usage:
    python scheduler.py              # Normal run
    python scheduler.py --dry-run    # Test without making changes
    python scheduler.py --force      # Run even outside scheduled hours
"""

import os
import sys
import json
import asyncio
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml
import httpx
from dotenv import load_dotenv
from fastmcp import Client

# Load .env from parent directory (for local development)
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

# Load config
CONFIG_PATH = Path(__file__).parent / "config.yaml"
with open(CONFIG_PATH) as f:
    CONFIG = yaml.safe_load(f)

# Environment variables
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
SUPABASE_REFRESH_TOKEN = os.getenv("SUPABASE_REFRESH_TOKEN", "")

# MCP Server config
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "https://myAirCondition.fastmcp.app/mcp")
MCP_API_KEY = os.getenv("MCP_API_KEY", "")

# OpenRouter config
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-001")


def get_mcp_client() -> Client:
    """Create an MCP client with API key auth."""
    if not MCP_API_KEY:
        raise RuntimeError("MCP_API_KEY not set")
    config = {
        "mcpServers": {
            "ac": {
                "transport": "http",
                "url": MCP_SERVER_URL,
                "headers": {"X-API-Key": MCP_API_KEY},
            }
        }
    }
    return Client(config)


async def get_room_conditions(mcp_client: Client) -> dict:
    """Get current room temperature and humidity from SwitchBot Hub 2."""
    try:
        result = await mcp_client.call_tool("get_room_temperature", {})
        # Parse the result - it returns a formatted string
        text = str(result)
        # Extract temperature and humidity from the response
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


async def get_ac_status(mcp_client: Client) -> dict:
    """Get current AC status."""
    try:
        result = await mcp_client.call_tool("get_ac_status", {})
        # Parse the result - it returns a formatted string
        text = str(result)
        status = {
            "power": "off",
            "temperature": None,
            "mode": None,
            "fan_speed": None,
        }
        for line in text.split("\n"):
            if "Power:" in line:
                status["power"] = "on" if "ON" in line.upper() else "off"
            elif "Temperature:" in line:
                try:
                    status["temperature"] = int(line.split(":")[1].replace("°C", "").strip())
                except:
                    pass
            elif "Mode:" in line:
                status["mode"] = line.split(":")[1].strip().lower()
            elif "Fan Speed:" in line:
                status["fan_speed"] = line.split(":")[1].strip().lower()
        return status
    except Exception as e:
        return {"error": str(e)}


async def get_weather() -> dict:
    """Get current weather from Open-Meteo (free, no API key required)."""
    lat = CONFIG["location"]["lat"]
    lon = CONFIG["location"]["lon"]
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            data = response.json()

            if response.status_code != 200:
                return {"error": data.get("reason", "Weather API error")}

            current = data.get("current", {})

            # Map weather codes to descriptions
            weather_codes = {
                0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast",
                45: "foggy", 48: "foggy", 51: "light drizzle", 53: "drizzle", 55: "heavy drizzle",
                61: "light rain", 63: "rain", 65: "heavy rain", 80: "rain showers",
                95: "thunderstorm", 96: "thunderstorm with hail"
            }
            weather_code = current.get("weather_code", 0)
            description = weather_codes.get(weather_code, "unknown")

            return {
                "temperature": current.get("temperature_2m"),
                "feels_like": current.get("apparent_temperature"),
                "humidity": current.get("relative_humidity_2m"),
                "description": description,
            }
    except Exception as e:
        return {"error": str(e)}


async def get_history_from_supabase() -> list:
    """Get recent AC decisions from Supabase."""
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        return []

    try:
        async with httpx.AsyncClient() as client:
            # Get last 24 hours of decisions
            response = await client.get(
                f"{SUPABASE_URL}/rest/v1/ac_automation_logs",
                params={
                    "select": "*",
                    "order": "created_at.desc",
                    "limit": "10",
                },
                headers={
                    "apikey": SUPABASE_ANON_KEY,
                    "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
                },
            )
            if response.status_code == 200:
                return response.json()
            return []
    except Exception:
        return []


async def log_to_supabase(data: dict) -> bool:
    """Log reading and decision to Supabase."""
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        print("Supabase not configured, skipping log")
        return False

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{SUPABASE_URL}/rest/v1/ac_automation_logs",
                json=data,
                headers={
                    "apikey": SUPABASE_ANON_KEY,
                    "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal",
                },
            )
            return response.status_code == 201
    except Exception as e:
        print(f"Failed to log to Supabase: {e}")
        return False


async def ask_ai_for_decision(context: dict) -> dict:
    """Ask OpenRouter AI for AC adjustment decision."""
    if not OPENROUTER_API_KEY:
        return {"error": "OPENROUTER_API_KEY not set", "action": "none"}

    rules = CONFIG["rules"]
    ai_notes = CONFIG.get("ai", {}).get("notes", "")

    prompt = f"""You are an AI assistant controlling a home air conditioner at night while the user sleeps.

CURRENT CONDITIONS:
- Room temperature: {context.get('room_temp', 'unknown')}°C
- Room humidity: {context.get('room_humidity', 'unknown')}%
- Outside temperature: {context.get('outside_temp', 'unknown')}°C
- Outside feels like: {context.get('outside_feels_like', 'unknown')}°C
- Weather: {context.get('weather_desc', 'unknown')}
- Current time: {context.get('current_time', 'unknown')}

AC STATUS:
- Power: {context.get('ac_power', 'unknown')}
- Set temperature: {context.get('ac_temp', 'unknown')}°C
- Mode: {context.get('ac_mode', 'unknown')}
- Fan speed: {context.get('ac_fan', 'unknown')}

RULES:
- Min temperature setting: {rules['min_temperature']}°C
- Max temperature setting: {rules['max_temperature']}°C
- Target comfort temperature: {rules['target_temperature']}°C
- Turn off AC if outside below: {rules['turn_off_when_outside_below']}°C
- Turn off AC if room below: {rules['turn_off_when_room_below']}°C
- Preferred mode: {rules.get('preferred_mode', 'cool')}

USER NOTES:
{ai_notes}

RECENT HISTORY:
{json.dumps(context.get('history', [])[:3], indent=2)}

Based on this information, decide what action to take. You must respond with ONLY a JSON object (no markdown, no explanation):

{{
  "action": "none" | "turn_on" | "turn_off" | "adjust_temp" | "change_mode",
  "temperature": <number 16-30 or null>,
  "mode": "cool" | "heat" | "auto" | "fan" | "dry" | null,
  "fan_speed": "auto" | "low" | "medium" | "high" | null,
  "reasoning": "<brief explanation>"
}}

If no change is needed, use action "none". Be conservative - only make changes when clearly beneficial for sleep comfort."""

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                json={
                    "model": OPENROUTER_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 200,
                },
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )

            if response.status_code != 200:
                return {"error": f"OpenRouter API error: {response.status_code}", "action": "none"}

            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()

            # Parse JSON from response (handle markdown code blocks)
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]

            return json.loads(content)

    except json.JSONDecodeError as e:
        return {"error": f"Failed to parse AI response: {e}", "action": "none"}
    except Exception as e:
        return {"error": str(e), "action": "none"}


async def execute_action(mcp_client: Client, decision: dict, dry_run: bool = False) -> dict:
    """Execute the AI's decision using MCP tools."""
    action = decision.get("action", "none")

    if action == "none":
        return {"executed": False, "reason": "No action needed"}

    if dry_run:
        return {"executed": False, "reason": f"Dry run - would execute: {action}"}

    try:
        # Get defaults from config
        default_temp = CONFIG["rules"]["target_temperature"]
        default_mode = CONFIG["rules"].get("preferred_mode", "cool")

        if action == "turn_off":
            result = await mcp_client.call_tool("set_ac_all_settings", {
                "power": "off",
                "temperature": default_temp,
                "mode": default_mode,
                "fan_speed": "auto",
            })

        elif action == "turn_on":
            result = await mcp_client.call_tool("set_ac_all_settings", {
                "power": "on",
                "temperature": decision.get("temperature", default_temp),
                "mode": decision.get("mode", default_mode),
                "fan_speed": decision.get("fan_speed", "auto"),
            })

        elif action == "adjust_temp":
            temp = decision.get("temperature")
            if not temp:
                return {"executed": False, "reason": "No temperature specified"}
            result = await mcp_client.call_tool("set_ac_all_settings", {
                "power": "on",
                "temperature": temp,
                "mode": decision.get("mode", default_mode),
                "fan_speed": decision.get("fan_speed", "auto"),
            })

        elif action == "change_mode":
            mode = decision.get("mode")
            if not mode:
                return {"executed": False, "reason": "No mode specified"}
            result = await mcp_client.call_tool("set_ac_all_settings", {
                "power": "on",
                "temperature": decision.get("temperature", default_temp),
                "mode": mode,
                "fan_speed": decision.get("fan_speed", "auto"),
            })

        else:
            return {"executed": False, "reason": f"Unknown action: {action}"}

        # Check if result contains success indicator
        result_str = str(result)
        if "✓" in result_str or "success" in result_str.lower():
            return {"executed": True, "result": result_str}
        else:
            return {"executed": False, "reason": result_str}

    except Exception as e:
        return {"executed": False, "reason": str(e)}


def is_within_schedule() -> bool:
    """Check if current time is within scheduled hours."""
    tz = ZoneInfo(CONFIG["location"]["timezone"])
    now = datetime.now(tz)
    hour = now.hour

    start = CONFIG["schedule"]["start_hour"]
    end = CONFIG["schedule"]["end_hour"]

    # Handle overnight schedule (e.g., 22:00 to 07:00)
    if start > end:
        return hour >= start or hour < end
    else:
        return start <= hour < end


async def main():
    parser = argparse.ArgumentParser(description="AC Night Automation")
    parser.add_argument("--dry-run", action="store_true", help="Test without making changes")
    parser.add_argument("--force", action="store_true", help="Run even outside scheduled hours")
    args = parser.parse_args()

    tz = ZoneInfo(CONFIG["location"]["timezone"])
    now = datetime.now(tz)
    print(f"\n{'='*50}")
    print(f"AC Night Automation - {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"{'='*50}")

    # Check schedule
    if not args.force and not is_within_schedule():
        print(f"Outside scheduled hours ({CONFIG['schedule']['start_hour']}:00-{CONFIG['schedule']['end_hour']}:00)")
        print("Use --force to run anyway")
        return

    # Connect to MCP server
    print("\n[0/5] Connecting to MCP server...")
    mcp_client = get_mcp_client()

    async with mcp_client:
        print(f"  Connected to {MCP_SERVER_URL}")

        # Gather all data
        print("\n[1/5] Getting room conditions...")
        room = await get_room_conditions(mcp_client)
        print(f"  Room: {room.get('temperature', '?')}°C, {room.get('humidity', '?')}% humidity")

        print("\n[2/5] Getting AC status...")
        ac_status = await get_ac_status(mcp_client)
        print(f"  AC: {ac_status.get('power', '?')}, {ac_status.get('temperature', '?')}°C, {ac_status.get('mode', '?')}")

        print("\n[3/5] Getting weather...")
        weather = await get_weather()
        print(f"  Outside: {weather.get('temperature', '?')}°C, {weather.get('description', '?')}")

        print("\n[4/5] Getting history...")
        history = await get_history_from_supabase()
        print(f"  Found {len(history)} recent decisions")

        # Build context for AI
        context = {
            "room_temp": room.get("temperature"),
            "room_humidity": room.get("humidity"),
            "outside_temp": weather.get("temperature"),
            "outside_feels_like": weather.get("feels_like"),
            "weather_desc": weather.get("description"),
            "current_time": now.strftime("%H:%M"),
            "ac_power": ac_status.get("power"),
            "ac_temp": ac_status.get("temperature"),
            "ac_mode": ac_status.get("mode"),
            "ac_fan": ac_status.get("fan_speed"),
            "history": history,
        }

        print("\n[5/5] Asking AI for decision...")
        decision = await ask_ai_for_decision(context)
        print(f"  Action: {decision.get('action', 'none')}")
        if decision.get('temperature'):
            print(f"  Temperature: {decision.get('temperature')}°C")
        if decision.get('mode'):
            print(f"  Mode: {decision.get('mode')}")
        if decision.get('fan_speed'):
            print(f"  Fan speed: {decision.get('fan_speed')}")
        print(f"  Reasoning: {decision.get('reasoning', 'N/A')}")

        if decision.get("error"):
            print(f"  Error: {decision['error']}")

        # Execute decision
        if decision.get("action") and decision["action"] != "none":
            print(f"\nExecuting action: {decision['action']}...")
            result = await execute_action(mcp_client, decision, dry_run=args.dry_run)
            print(f"  Result: {'Success' if result.get('executed') else result.get('reason')}")
        else:
            result = {"executed": False, "reason": "No action taken"}

        # Log to Supabase
        log_data = {
            "room_temperature": room.get("temperature"),
            "room_humidity": room.get("humidity"),
            "outside_temperature": weather.get("temperature"),
            "ac_power": ac_status.get("power"),
            "ac_temperature": ac_status.get("temperature"),
            "ac_mode": ac_status.get("mode"),
            "action": decision.get("action", "none"),
            "reasoning": decision.get("reasoning"),
            "executed": result.get("executed", False),
        }

        if not args.dry_run:
            await log_to_supabase(log_data)
            print("\nLogged to Supabase")

    print(f"\n{'='*50}")
    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
