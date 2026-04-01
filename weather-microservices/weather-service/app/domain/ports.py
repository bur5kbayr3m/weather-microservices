from abc import ABC, abstractmethod

from app.domain.models import WeatherData


class WeatherProvider(ABC):
    @abstractmethod
    def get_current_weather(self, city: str) -> WeatherData:
        raise NotImplementedError


class EventPublisher(ABC):
    @abstractmethod
    def publish_weather_requested(self, payload: dict) -> None:
        raise NotImplementedError
