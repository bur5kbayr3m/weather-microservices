import requests

from app.domain.models import WeatherData
from app.domain.ports import WeatherProvider


class OpenMeteoWeatherProvider(WeatherProvider):
    GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
    WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

    def get_current_weather(self, city: str) -> WeatherData:
        geo_response = requests.get(self.GEO_URL, params={"name": city, "count": 1}, timeout=8)
        geo_response.raise_for_status()
        geo_data = geo_response.json()
        results = geo_data.get("results", [])
        if not results:
            raise ValueError(f"City not found: {city}")

        top_result = results[0]
        latitude = top_result["latitude"]
        longitude = top_result["longitude"]
        normalized_city = top_result["name"]

        weather_response = requests.get(
            self.WEATHER_URL,
            params={
                "latitude": latitude,
                "longitude": longitude,
                "current": (
                    "temperature_2m,relative_humidity_2m,precipitation,"
                    "cloud_cover,wind_speed_10m,weather_code"
                ),
            },
            timeout=8,
        )
        weather_response.raise_for_status()
        weather_data = weather_response.json().get("current", {})

        return WeatherData(
            city=normalized_city,
            latitude=latitude,
            longitude=longitude,
            temperature_c=weather_data.get("temperature_2m", 0.0),
            humidity_percent=weather_data.get("relative_humidity_2m", 0.0),
            precipitation_mm=weather_data.get("precipitation", 0.0),
            cloud_cover_percent=weather_data.get("cloud_cover", 0.0),
            wind_speed_kmh=weather_data.get("wind_speed_10m", 0.0),
            weather_code=weather_data.get("weather_code", -1),
        )
