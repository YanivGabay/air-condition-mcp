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

    optimal_min = rules.get("optimal_min", 16)
    optimal_max = rules.get("optimal_max", 20)
    acceptable_max = rules.get("acceptable_max", 24)

    prompt = f"""You are an AI controlling a home AC at night. User sleeps WITH A BLANKET.

CURRENT CONDITIONS:
- Room: {context.get('room_temp', 'unknown')}°C, {context.get('room_humidity', 'unknown')}% humidity
- Outside: {context.get('outside_temp', 'unknown')}°C (feels like {context.get('outside_feels_like', 'unknown')}°C)
- Weather: {context.get('weather_desc', 'unknown')}
- Time: {context.get('current_time', 'unknown')}

AC STATUS:
- Power: {context.get('ac_power', 'unknown')}
- Temperature: {context.get('ac_temp', 'unknown')}°C
- Mode: {context.get('ac_mode', 'unknown')}

SLEEP SCIENCE (user sleeps with blanket):
- OPTIMAL: {optimal_min}-{optimal_max}°C (cool room + blanket = best sleep)
- ACCEPTABLE: {optimal_max}-{acceptable_max}°C (comfortable, no AC needed)
- TOO HOT: >{acceptable_max}°C (need cooling)
- TOO COLD: <{optimal_min}°C (need heating)

DECISION LOGIC:
1. Room {optimal_min}-{acceptable_max}°C → "none" or "turn_off" (comfortable range)
2. Room >{acceptable_max}°C → COOL mode (too hot)
3. Room <{optimal_min}°C → HEAT mode (too cold)
4. If AC is ON but room is comfortable → "turn_off" (save energy)
5. If outside is cold and room is fine → "turn_off" (natural cooling works)

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
