"""
Weather API

Fetch weather data from Open-Meteo (free, no API key required).
"""

import httpx


WEATHER_CODES = {
    0: "clear sky",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "foggy",
    48: "foggy",
    51: "light drizzle",
    53: "drizzle",
    55: "heavy drizzle",
    61: "light rain",
    63: "rain",
    65: "heavy rain",
    80: "rain showers",
    95: "thunderstorm",
    96: "thunderstorm with hail",
}


async def get_weather(lat: float, lon: float) -> dict:
    """Get current weather from Open-Meteo."""
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code"
    )

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            data = response.json()

            if response.status_code != 200:
                return {"error": data.get("reason", "Weather API error")}

            current = data.get("current", {})
            code = current.get("weather_code", 0)

            return {
                "temperature": current.get("temperature_2m"),
                "feels_like": current.get("apparent_temperature"),
                "humidity": current.get("relative_humidity_2m"),
                "description": WEATHER_CODES.get(code, "unknown"),
            }
    except Exception as e:
        return {"error": str(e)}
