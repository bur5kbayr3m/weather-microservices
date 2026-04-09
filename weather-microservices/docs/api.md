# API Documentation

## API Gateway

Base URL: `http://localhost:8080`

### POST /api/v1/login
Request body:
```json
{
  "username": "student",
  "password": "student123"
}
```
Response:
```json
{
  "access_token": "<jwt>",
  "token_type": "bearer"
}
```

### GET /api/v1/weather?city=Istanbul&notify=email@example.com
Headers:
- `Authorization: Bearer <jwt>`

Response:
```json
{
  "city": "Istanbul",
  "latitude": 41.01,
  "longitude": 28.95,
  "temperature_c": 21.3,
  "humidity_percent": 63,
  "precipitation_mm": 0.0,
  "cloud_cover_percent": 35,
  "wind_speed_kmh": 9.4,
  "weather_code": 1
}
```

### POST /api/v1/outfit
Headers:
- `Authorization: Bearer <jwt>`

Request body:
```json
{
  "temperature_c": 21.3,
  "humidity_percent": 63,
  "precipitation_mm": 0.0,
  "cloud_cover_percent": 35,
  "wind_speed_kmh": 9.4,
  "weather_code": 1
}
```

Response:
```json
{
  "title": "Ilık Hava Kombini",
  "mood": "denge ve rahatlık",
  "colors": ["krem", "camel", "açık gri", "zeytin yeşili"],
  "pieces": ["İnce triko veya gömlek", "Straight fit jean veya chino pantolon"],
  "weather_note": "Hava dengeli; smart casual bir kombin iyi çalışır."
}
```

### GET /health
Returns service health.

## Auth Service
Base URL: `http://localhost:5001`

- `POST /login`
- `POST /verify`
- `GET /health`

## Weather Service
Base URL: `http://localhost:5002`

- `GET /weather?city=Istanbul&notify=email@example.com`
- `GET /health`

## Notification Service
Base URL: `http://localhost:5003`

- `GET /notifications`
- `GET /health`
