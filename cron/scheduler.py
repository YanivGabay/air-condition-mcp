#!/usr/bin/env python3
"""
AC Night Automation Scheduler

Runs every hour at night to adjust AC based on room conditions and sleep science.

Usage:
    python scheduler.py              # Normal run
    python scheduler.py --dry-run    # Test without changes
    python scheduler.py --force      # Run outside schedule
"""

import os
import sys
import asyncio
import argparse
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml
from dotenv import load_dotenv

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.automation import (
    get_weather,
    ask_ai_for_decision,
    log_to_supabase,
    get_history,
    create_mcp_client,
    get_room_conditions,
    get_ac_status,
    execute_action,
)

# Load .env from parent
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

# Load config
CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"
with open(CONFIG_PATH) as f:
    CONFIG = yaml.safe_load(f)

# Environment
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-001")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "")
MCP_API_KEY = os.getenv("MCP_API_KEY", "")


def is_within_schedule() -> bool:
    """Check if current time is within scheduled hours."""
    tz = ZoneInfo(CONFIG["location"]["timezone"])
    hour = datetime.now(tz).hour
    start = CONFIG["schedule"]["start_hour"]
    end = CONFIG["schedule"]["end_hour"]

    if start > end:  # Overnight (e.g., 22:00 to 07:00)
        return hour >= start or hour < end
    return start <= hour < end


def is_final_run() -> bool:
    """Check if this is the last run before wake up."""
    tz = ZoneInfo(CONFIG["location"]["timezone"])
    hour = datetime.now(tz).hour
    end = CONFIG["schedule"]["end_hour"]
    return hour == end - 1


async def main():
    parser = argparse.ArgumentParser(description="AC Night Automation")
    parser.add_argument("--dry-run", action="store_true", help="Test without changes")
    parser.add_argument("--force", action="store_true", help="Run outside schedule")
    args = parser.parse_args()

    tz = ZoneInfo(CONFIG["location"]["timezone"])
    now = datetime.now(tz)

    print(f"\n{'='*50}")
    print(f"AC Night Automation - {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"{'='*50}")

    # Check schedule
    if not args.force and not is_within_schedule():
        print(f"Outside scheduled hours. Use --force to run anyway.")
        return

    # Connect to MCP
    print("\n[1/5] Connecting to MCP server...")
    mcp_client = create_mcp_client(MCP_SERVER_URL, MCP_API_KEY)

    async with mcp_client:
        print(f"  Connected to {MCP_SERVER_URL}")

        # Gather data
        print("\n[2/5] Getting room conditions...")
        room = await get_room_conditions(mcp_client)
        print(f"  Room: {room.get('temperature', '?')}°C, {room.get('humidity', '?')}%")

        print("\n[3/5] Getting AC status...")
        ac = await get_ac_status(mcp_client)
        print(f"  AC: {ac.get('power', '?')}, {ac.get('temperature', '?')}°C")

        print("\n[4/5] Getting weather...")
        weather = await get_weather(CONFIG["location"]["lat"], CONFIG["location"]["lon"])
        print(f"  Outside: {weather.get('temperature', '?')}°C")

        # Build context
        context = {
            "room_temp": room.get("temperature"),
            "room_humidity": room.get("humidity"),
            "outside_temp": weather.get("temperature"),
            "outside_feels_like": weather.get("feels_like"),
            "weather_desc": weather.get("description"),
            "current_time": now.strftime("%H:%M"),
            "ac_power": ac.get("power"),
            "ac_temp": ac.get("temperature"),
            "ac_mode": ac.get("mode"),
            "history": await get_history(SUPABASE_URL, SUPABASE_ANON_KEY),
        }

        # Get decision
        if is_final_run():
            print("\n[5/5] Final run - turning off AC...")
            decision = {"action": "turn_off", "reasoning": "Final run before wake up"}
        else:
            print("\n[5/5] Asking AI for decision...")
            decision = await ask_ai_for_decision(
                OPENROUTER_API_KEY, OPENROUTER_MODEL, context, CONFIG
            )

        print(f"  Action: {decision.get('action', 'none')}")
        print(f"  Reasoning: {decision.get('reasoning', 'N/A')}")

        # Execute
        if decision.get("action") and decision["action"] != "none":
            if args.dry_run:
                print(f"\n  [DRY RUN] Would execute: {decision['action']}")
                result = {"executed": False, "reason": "Dry run"}
            else:
                print(f"\nExecuting: {decision['action']}...")
                result = await execute_action(mcp_client, decision, CONFIG)
                print(f"  Result: {'Success' if result.get('executed') else result.get('reason')}")
        else:
            result = {"executed": False, "reason": "No action"}

        # Log
        if not args.dry_run:
            await log_to_supabase(
                SUPABASE_URL,
                SUPABASE_ANON_KEY,
                {
                    "room_temperature": room.get("temperature"),
                    "room_humidity": room.get("humidity"),
                    "outside_temperature": weather.get("temperature"),
                    "ac_power": ac.get("power"),
                    "ac_temperature": ac.get("temperature"),
                    "ac_mode": ac.get("mode"),
                    "action": decision.get("action", "none"),
                    "reasoning": decision.get("reasoning"),
                    "executed": result.get("executed", False),
                },
            )
            print("\nLogged to Supabase")

    print(f"\n{'='*50}")
    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
