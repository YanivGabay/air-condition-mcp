---
name: ac-status
description: Check current AC and room status. Use when user asks about room temperature, humidity, AC power state, current AC settings, or wants to see the current conditions.
---

# Check AC and Room Status

Get current conditions from Hub 2 and AC.

## Using MCP Tools

If Supabase MCP connected, use these tools:
- `get_room_temperature` - Room temp and humidity from Hub 2
- `get_ac_status` - AC power, temp, mode, fan speed

## Quick Script

Run from the project root directory:

```bash
source venv/bin/activate && python3 << 'EOF'
import asyncio, os
from fastmcp import Client
from dotenv import load_dotenv
load_dotenv()

async def check():
    config = {"mcpServers": {"ac": {"transport": "http", "url": os.getenv("MCP_SERVER_URL"), "headers": {"X-API-Key": os.getenv("MCP_API_KEY")}}}}
    async with Client(config) as c:
        r = await c.call_tool("get_room_temperature", {})
        print("=== Room ===\n" + (r.data if hasattr(r, 'data') else str(r)))
        r = await c.call_tool("get_ac_status", {})
        print("\n=== AC ===\n" + (r.data if hasattr(r, 'data') else str(r)))
asyncio.run(check())
EOF
```

## Outside Weather

```bash
curl -s "https://api.open-meteo.com/v1/forecast?latitude=31.8928&longitude=35.0104&current=temperature_2m,apparent_temperature" | python3 -c "import json,sys;d=json.load(sys.stdin)['current'];print(f\"Outside: {d['temperature_2m']}C (feels {d['apparent_temperature']}C)\")"
```
