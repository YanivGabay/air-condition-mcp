---
name: ac-test
description: Test the AC night automation scheduler in dry-run mode. Use when user wants to test, preview, or debug what the AC automation would do without actually controlling the AC.
---

# AC Scheduler Dry Run

Test the night automation without making actual AC changes.

## Command

```bash
source venv/bin/activate && python3 cron/scheduler.py --dry-run --force
```

Run from the project root directory.

## What It Does

1. Connects to MCP server
2. Gets room temperature/humidity
3. Gets AC status
4. Gets outside weather
5. Asks AI for decision based on sleep science
6. Shows what action would be taken (without executing)

## Troubleshooting

- "MCP_API_KEY not set": Check `.env` file exists with key
- Connection failed: Check MCP_SERVER_URL in .env
