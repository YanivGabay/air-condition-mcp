"""
SwitchBot Air Conditioner MCP Server

Control your AC through SwitchBot Hub 2 using MCP.
"""

import os
import sys
from pathlib import Path

from fastmcp import FastMCP

# Load .env file
try:
    from dotenv import load_dotenv
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        load_dotenv(env_file)
except ImportError:
    pass

# Import modules
from src.switchbot import SwitchBotClient, ACCommands
from src.tools import register_ac_control_tools, register_status_tools, register_discovery_tools

# Configuration
SWITCHBOT_TOKEN = os.getenv("SWITCHBOT_TOKEN", "")
SWITCHBOT_SECRET = os.getenv("SWITCHBOT_SECRET", "")
AC_DEVICE_ID = os.getenv("SWITCHBOT_AC_DEVICE_ID", "")

# Debug logging
if not SWITCHBOT_TOKEN:
    print("⚠️ WARNING: SWITCHBOT_TOKEN is empty!", file=sys.stderr)
if not SWITCHBOT_SECRET:
    print("⚠️ WARNING: SWITCHBOT_SECRET is empty!", file=sys.stderr)
if not AC_DEVICE_ID:
    print("⚠️ WARNING: SWITCHBOT_AC_DEVICE_ID is empty!", file=sys.stderr)

if SWITCHBOT_TOKEN and SWITCHBOT_SECRET and AC_DEVICE_ID:
    print("✅ Environment variables loaded", file=sys.stderr)
    print(f"   Device ID: {AC_DEVICE_ID}", file=sys.stderr)

# Initialize components
mcp = FastMCP("SwitchBot AC Controller")
client = SwitchBotClient(SWITCHBOT_TOKEN, SWITCHBOT_SECRET)
ac = ACCommands(client, AC_DEVICE_ID)

# Register all tools
register_ac_control_tools(mcp, ac)
register_status_tools(mcp, ac)
register_discovery_tools(mcp, client, AC_DEVICE_ID)


if __name__ == "__main__":
    mcp.run()
