---
name: ac-run
description: Run the AC night automation scheduler to make a real decision and control the AC. Use when user wants to manually trigger the automation, force an AC adjustment, or run the scheduler outside scheduled hours.
---

# AC Scheduler Manual Run

Run the automation to make a real AC decision and execute it.

## Command

```bash
source venv/bin/activate && python3 cron/scheduler.py --force
```

Run from the project root directory.

## What It Does

1. Gets room conditions and weather
2. AI decides based on sleep science (16-20C optimal with blanket)
3. Executes AC command via MCP
4. Logs to Supabase

## Warning

This WILL control the AC. Use `/ac-test` first to preview.
