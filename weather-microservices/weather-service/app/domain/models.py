from dataclasses import asdict, dataclass


@dataclass
class WeatherData:
    city: str
    latitude: float
    longitude: float
    temperature_c: float
    wind_speed_kmh: float
    weather_code: int

    def to_dict(self) -> dict:
        return asdict(self)
