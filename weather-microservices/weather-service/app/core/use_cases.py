from app.domain.models import WeatherData
from app.domain.ports import EventPublisher, WeatherProvider


class GetWeatherUseCase:
    def __init__(self, weather_provider: WeatherProvider, event_publisher: EventPublisher):
        self.weather_provider = weather_provider
        self.event_publisher = event_publisher

    def execute(self, city: str, notify_target: str | None = None) -> WeatherData:
        weather = self.weather_provider.get_current_weather(city)
        self.event_publisher.publish_weather_requested(
            {
                "city": weather.city,
                "temperature_c": weather.temperature_c,
                "notify_target": notify_target,
            }
        )
        return weather
