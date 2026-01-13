"""
AI Decision Making

Use OpenRouter to make AC decisions based on sleep science.
"""

import json
import httpx


async def ask_ai_for_decision(
    api_key: str,
    model: str,
    context: dict,
    config: dict,
) -> dict:
    """Ask AI for AC adjustment decision."""
    if not api_key:
        return {"error": "OPENROUTER_API_KEY not set", "action": "none"}

    rules = config.get("rules", {})
    ai_notes = config.get("ai", {}).get("notes", "")
    room_layout = config.get("room", {}).get("layout", "")

    # Get current month for season context
    from datetime import datetime
    current_month = datetime.now().month
    season = "winter" if current_month in [12, 1, 2] else "spring" if current_month in [3, 4, 5] else "summer" if current_month in [6, 7, 8] else "autumn"

    prompt = f"""You control a bedroom AC. Decide what's best for sleep.

DATA:
- Room sensor: {context.get('room_temp', 'unknown')}°C, {context.get('room_humidity', 'unknown')}% humidity
- Outside: {context.get('outside_temp', 'unknown')}°C
- Weather: {context.get('weather_desc', 'unknown')}
- Season: {season} (month: {current_month})
- Time: {context.get('current_time', 'unknown')}
- Location: Israel

AC:
- Power: {context.get('ac_power', 'unknown')}
- Set to: {context.get('ac_temp', 'unknown')}°C, mode: {context.get('ac_mode', 'unknown')}

USER:
- Sleeps with thick blanket (פוך)
- Wakes ~06:30

ROOM LAYOUT:
{room_layout}

{ai_notes}

HISTORY: {json.dumps(context.get('history', [])[:2], indent=2)}

Respond with ONLY JSON:
{{"action": "none"|"turn_on"|"turn_off"|"adjust_temp"|"change_mode", "temperature": <number or null>, "mode": "cool"|"heat"|"auto"|"fan"|"dry"|null, "fan_speed": "auto"|"low"|"medium"|"high"|null, "reasoning": "<brief>"}}"""

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 200,
                },
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )

            if response.status_code != 200:
                return {"error": f"API error: {response.status_code}", "action": "none"}

            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()

            # Parse JSON (handle markdown code blocks)
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]

            return json.loads(content)

    except json.JSONDecodeError as e:
        return {"error": f"Failed to parse AI response: {e}", "action": "none"}
    except Exception as e:
        return {"error": str(e), "action": "none"}
