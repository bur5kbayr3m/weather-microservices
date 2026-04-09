from dataclasses import asdict, dataclass


@dataclass
class WeatherData:
    city: str
    latitude: float
    longitude: float
    temperature_c: float
    humidity_percent: float
    precipitation_mm: float
    cloud_cover_percent: float
    wind_speed_kmh: float
    weather_code: int

    def to_dict(self) -> dict:
        return asdict(self)
