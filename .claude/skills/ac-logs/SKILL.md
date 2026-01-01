---
name: ac-logs
description: View recent AC automation logs from Supabase. Use when user wants to see history, check what decisions were made, debug past automation runs, or review AC control history.
---

# View AC Automation Logs

Query Supabase for recent automation decisions.

## Using Supabase MCP

```sql
SELECT created_at, room_temperature, outside_temperature, ac_power, action, reasoning, executed
FROM ac_automation_logs
ORDER BY created_at DESC
LIMIT 10;
```

## Using curl

```bash
source .env && \
curl -s "${SUPABASE_URL}/rest/v1/ac_automation_logs?select=*&order=created_at.desc&limit=10" \
  -H "apikey: ${SUPABASE_ANON_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_ANON_KEY}" | python3 -m json.tool
```

Run from the project root directory.

## Fields

- `room_temperature`, `outside_temperature` - Temps in Celsius
- `action` - none/turn_on/turn_off/adjust_temp/change_mode
- `reasoning` - AI's explanation
- `executed` - Whether action was run
