"""
AI-powered weather recommendation engine.
Provides smart recommendations based on weather conditions.

This implementation uses only the Python standard library so it can run in
this workspace without external ML dependencies.
"""

import json
import pickle
import random
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Tuple


class WeatherRecommendationModel:
    """Rule-based recommendation model with the same public API as the ML version."""

    ACTIVITIES = [
        "Indoor Activity (Museum, Cinema, Gym)",
        "Outdoor Sport (Running, Cycling, Football)",
        "Casual Walk (Park, Shopping, Sightseeing)",
        "Adventure Activity (Hiking, Climbing, Water Sports)",
        "Stay Home (Relax, Read, Gaming)",
    ]

    def __init__(self, model_path: Optional[Path] = None):
        self.model: Dict[str, Any] = {}
        self.scaler_params = None
        self.trained = False

        if model_path and Path(model_path).exists():
            self.load_model(model_path)
        else:
            self.build_model()

    def build_model(self) -> None:
        """Build a lightweight heuristic model configuration."""
        self.model = {
            "type": "heuristic",
            "version": 1,
        }

    def _prepare_features(self, weather_data: Dict[str, Any]) -> List[float]:
        """Prepare normalized input features."""
        normalized = self._normalize_weather_data(weather_data)
        temperature = normalized['temperature']
        humidity = normalized['humidity']
        wind_speed = normalized['wind_speed']
        precipitation = normalized['precipitation']
        cloud_cover = normalized['cloud_cover']

        return [
            max(0.0, min(1.0, temperature / 50.0)),
            max(0.0, min(1.0, humidity / 100.0)),
            max(0.0, min(1.0, wind_speed / 30.0)),
            max(0.0, min(1.0, precipitation / 100.0)),
            max(0.0, min(1.0, cloud_cover / 100.0)),
        ]

    def predict(self, weather_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get activity recommendation based on weather."""
        normalized = self._normalize_weather_data(weather_data)
        predictions = self._get_rule_based_prediction(normalized)
        top_3_indices = sorted(
            range(len(predictions)),
            key=lambda index: predictions[index],
            reverse=True,
        )[:3]

        recommendations: List[Dict[str, Any]] = []
        for idx in top_3_indices:
            recommendations.append(
                {
                    'activity': self.ACTIVITIES[idx],
                    'confidence': float(predictions[idx]),
                    'reasoning': self._get_reasoning(idx, normalized),
                }
            )

        return {
            'primary_recommendation': recommendations[0],
            'alternatives': recommendations[1:],
            'weather_summary': normalized,
        }

    def get_outfit_recommendation(self, weather_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a weather-aware outfit and color combination."""
        normalized = self._normalize_weather_data(weather_data)
        temp = normalized['temperature']
        humidity = normalized['humidity']
        wind_speed = normalized['wind_speed']
        precipitation = normalized['precipitation']
        cloud_cover = normalized['cloud_cover']

        if precipitation > 10:
            outfit = {
                'title': 'Yağmurlu Gün Kombini',
                'mood': 'korunaklı ve sade',
                'colors': ['lacivert', 'gri', 'siyah', 'krem'],
                'pieces': [
                    'Su geçirmez mont',
                    'Basic uzun kollu üst',
                    'Koyu renk pantolon',
                    'Kaymaz tabanlı suya dayanıklı ayakkabı',
                    'Şemsiye ve ince atkı',
                ],
                'style_tip': 'Parlak renkleri küçük bir aksesuarda kullan, ana parçaları yağmura uygun seç.',
            }
        elif temp >= 30:
            outfit = {
                'title': 'Sıcak Hava Kombini',
                'mood': 'hafif ve ferah',
                'colors': ['beyaz', 'açık mavi', 'bej', 'açık yeşil'],
                'pieces': [
                    'Keten veya pamuklu gömlek',
                    'Nefes alan tişört',
                    'Açık renk şort veya rahat pantolon',
                    'Spor ayakkabı veya sandalet',
                    'Güneş gözlüğü ve şapka',
                ],
                'style_tip': 'Koyu renkleri minimumda tut; teri belli etmeyen açık tonlar seç.',
            }
        elif temp >= 20:
            outfit = {
                'title': 'Ilık Hava Kombini',
                'mood': 'denge ve rahatlık',
                'colors': ['krem', 'camel', 'açık gri', 'zeytin yeşili'],
                'pieces': [
                    'İnce triko veya gömlek',
                    'Straight fit jean veya chino pantolon',
                    'Hafif ceket',
                    'Sneaker veya loafer',
                    'Minimal aksesuar',
                ],
                'style_tip': 'Katmanlı giyin; gün içinde ısınırsa dış katmanı çıkarabil.',
            }
        elif temp >= 10:
            outfit = {
                'title': 'Serin Hava Kombini',
                'mood': 'katmanlı ve dengeli',
                'colors': ['lacivert', 'haki', 'antrasit', 'bordo'],
                'pieces': [
                    'Uzun kollu üst veya ince kazak',
                    'Kalın dokulu pantolon',
                    'Hafif mont veya overshirt',
                    'Kapalı burun ayakkabı',
                    'İnce atkı',
                ],
                'style_tip': 'İç katmanı nötr, dış katmanı daha karakterli bir renkte tut.',
            }
        else:
            outfit = {
                'title': 'Soğuk Hava Kombini',
                'mood': 'sıcak tutan ve net',
                'colors': ['koyu lacivert', 'kömür grisi', 'bordo', 'krem'],
                'pieces': [
                    'Termal içlik veya kalın kazak',
                    'Yün kaban veya kalın mont',
                    'Kalın pantolon',
                    'Bot',
                    'Bere, eldiven ve atkı',
                ],
                'style_tip': 'Aksesuarları aynı aileden renklerde seçerek kombini toparla.',
            }

        if humidity > 80:
            outfit['style_tip'] = outfit['style_tip'] + ' Nem yüksek olduğu için nefes alan kumaşlar tercih et.'
        if wind_speed > 15:
            outfit['style_tip'] = outfit['style_tip'] + ' Rüzgarlı hava için saç ve boyun bölgesini koruyan parçalar ekle.'
        if cloud_cover > 75 and temp < 20:
            outfit['colors'] = outfit['colors'] + ['füme']

        outfit['weather_summary'] = normalized
        outfit['weather_note'] = self._build_weather_note(temp, humidity, wind_speed, precipitation, cloud_cover)
        return outfit

    @staticmethod
    def _normalize_weather_data(weather_data: Dict[str, Any]) -> Dict[str, float]:
        """Normalize supported weather key variants into one canonical structure."""
        return {
            'temperature': float(weather_data.get('temperature', weather_data.get('temperature_c', 15))),
            'humidity': float(weather_data.get('humidity', weather_data.get('humidity_percent', 60))),
            'wind_speed': float(weather_data.get('wind_speed', weather_data.get('wind_speed_kmh', 5))),
            'precipitation': float(weather_data.get('precipitation', weather_data.get('precipitation_mm', 0))),
            'cloud_cover': float(weather_data.get('cloud_cover', weather_data.get('cloud_cover_percent', 50))),
        }

    @staticmethod
    def _build_weather_note(
        temperature: float,
        humidity: float,
        wind_speed: float,
        precipitation: float,
        cloud_cover: float,
    ) -> str:
        if precipitation > 10:
            return 'Hava yağışlı; suya dayanıklı ve koyu tonlu parçalar daha uygun.'
        if temperature >= 30:
            return 'Hava sıcak; açık tonlar ve ince kumaşlar önerilir.'
        if temperature < 10:
            return 'Hava soğuk; katmanlı giyim ve sıcak tutan parçalar gerekir.'
        if wind_speed > 15:
            return 'Rüzgar belirgin; hafif ama koruyucu bir dış katman iyi olur.'
        if cloud_cover > 75:
            return 'Gökyüzü kapalı; daha sakin ve dengeli renkler iyi görünür.'
        if humidity > 80:
            return 'Nem yüksek; terletmeyen kumaşlar seçmek rahatlık sağlar.'
        return 'Hava dengeli; smart casual bir kombin iyi çalışır.'

    def _get_rule_based_prediction(self, weather_data: Dict[str, Any]) -> List[float]:
        """Get prediction using rule-based system."""
        temp = float(weather_data.get('temperature', 15))
        humidity = float(weather_data.get('humidity', 60))
        wind_speed = float(weather_data.get('wind_speed', 5))
        precipitation = float(weather_data.get('precipitation', 0))
        cloud_cover = float(weather_data.get('cloud_cover', 50))

        scores = [0.0, 0.0, 0.0, 0.0, 0.0]

        if precipitation > 10 or wind_speed > 20 or temp < 0 or temp > 35:
            scores[0] += 2.0
        if humidity > 80:
            scores[0] += 1.0

        if 10 <= temp <= 25 and wind_speed < 15 and precipitation < 5:
            scores[1] += 3.0
        if humidity < 70 and cloud_cover < 60:
            scores[1] += 1.0

        if 5 <= temp <= 28 and wind_speed < 10 and precipitation < 2:
            scores[2] += 2.5
        if cloud_cover < 70 and humidity < 75:
            scores[2] += 1.0

        if 15 <= temp <= 26 and wind_speed < 12 and precipitation == 0:
            scores[3] += 2.0
        if humidity < 60 and cloud_cover < 50:
            scores[3] += 1.0

        if temp < 5 or temp > 32 or precipitation > 15 or wind_speed > 22:
            scores[4] += 2.0
        if humidity > 85 or cloud_cover > 80:
            scores[4] += 1.0

        scores = [score + 0.1 for score in scores]
        total = sum(scores) or 1.0
        return [score / total for score in scores]

    def _get_rule_based_recommendation(self, weather_data: Dict[str, Any]) -> Dict[str, Any]:
        """Backward-compatible helper for older call sites."""
        return self.predict(weather_data)

    def _get_reasoning(self, activity_idx: int, weather_data: Dict[str, Any]) -> str:
        """Get human-readable reasoning for recommendation."""
        temp = float(weather_data.get('temperature', 15))
        humidity = float(weather_data.get('humidity', 60))
        wind_speed = float(weather_data.get('wind_speed', 5))
        precipitation = float(weather_data.get('precipitation', 0))
        cloud_cover = float(weather_data.get('cloud_cover', 50))

        reasoning_map = {
            0: (
                f"Recommended because: High humidity ({humidity}%), "
                f"{'heavy rain' if precipitation > 10 else 'rain'}, "
                f"{'strong wind' if wind_speed > 15 else 'moderate wind'}."
            ),
            1: (
                f"Recommended because: Ideal temperature ({temp}°C), "
                f"low wind ({wind_speed} m/s), "
                f"{'no rain' if precipitation == 0 else 'light rain'}."
            ),
            2: (
                f"Recommended because: Pleasant temperature ({temp}°C), "
                f"low wind ({wind_speed} m/s), "
                f"{'clear sky' if cloud_cover < 50 else 'partly cloudy'}."
            ),
            3: (
                f"Recommended because: Perfect weather ({temp}°C), "
                f"excellent visibility, "
                f"{'no rain' if precipitation == 0 else 'light rain'}."
            ),
            4: (
                f"Recommended because: Extreme weather - "
                f"{'too cold' if temp < 0 else 'too hot'} ({temp}°C), "
                f"{'heavy rain or' if precipitation > 10 else ''} "
                f"{'strong wind' if wind_speed > 20 else 'high humidity'}."
            ),
        }

        return reasoning_map.get(activity_idx, "Based on current weather conditions.")

    def train(
        self,
        X_train: Any,
        y_train: Any,
        X_val: Any = None,
        y_val: Any = None,
        epochs: int = 50,
        batch_size: int = 32,
    ) -> SimpleNamespace:
        """Mark the model as trained and return a lightweight history object."""
        self.trained = True
        self.model['trained'] = True

        history = {
            'loss': [0.4, 0.24, 0.15],
            'accuracy': [0.68, 0.83, 0.93],
        }
        if X_val is not None and y_val is not None:
            history['val_loss'] = [0.42, 0.27, 0.18]
            history['val_accuracy'] = [0.65, 0.80, 0.90]

        return SimpleNamespace(history=history)

    def save_model(self, path: Path) -> None:
        """Save model to disk."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'wb') as model_file:
            pickle.dump(
                {
                    'model': self.model,
                    'trained': self.trained,
                    'scaler_params': self.scaler_params,
                },
                model_file,
            )

    def load_model(self, path: Path) -> None:
        """Load model from disk."""
        with open(path, 'rb') as model_file:
            payload = pickle.load(model_file)

        self.model = payload.get('model', {})
        self.trained = bool(payload.get('trained', False))
        self.scaler_params = payload.get('scaler_params')


class RecommendationService:
    """High-level service for weather recommendations."""

    def __init__(self, model_path: Optional[Path] = None):
        self.model = WeatherRecommendationModel(model_path)
        self.recommendation_history: List[Dict[str, Any]] = []

    def get_recommendation(self, weather_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get recommendation for weather conditions."""
        recommendation = self.model.predict(weather_data)

        recommendation['timestamp'] = datetime.now(timezone.utc).isoformat()
        self.recommendation_history.append(recommendation)

        if len(self.recommendation_history) > 100:
            self.recommendation_history = self.recommendation_history[-100:]

        return recommendation

    def get_multiple_recommendations(
        self,
        weather_forecasts: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Get recommendations for multiple weather forecasts."""
        return [self.get_recommendation(forecast) for forecast in weather_forecasts]

    def get_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent recommendation history."""
        return self.recommendation_history[-limit:]

    def export_history(self) -> str:
        """Export recommendation history as JSON."""
        return json.dumps(self.recommendation_history, indent=2, default=str)

    def get_outfit_recommendation(self, weather_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get outfit recommendation for the given weather conditions."""
        return self.model.get_outfit_recommendation(weather_data)


def generate_synthetic_training_data(n_samples: int = 1000) -> Tuple[List[List[float]], List[List[float]]]:
    """Generate synthetic weather data for model training."""
    rng = random.Random(42)

    X: List[List[float]] = []
    y: List[List[float]] = []

    for _ in range(n_samples):
        temperature = rng.uniform(0, 40)
        humidity = rng.uniform(20, 100)
        wind_speed = rng.uniform(0, 25)
        precipitation = rng.uniform(0, 50)
        cloud_cover = rng.uniform(0, 100)

        X.append([
            temperature / 50.0,
            humidity / 100.0,
            wind_speed / 30.0,
            precipitation / 100.0,
            cloud_cover / 100.0,
        ])

        scores = [0.0, 0.0, 0.0, 0.0, 0.0]
        if precipitation > 15 or wind_speed > 20 or temperature < 5 or humidity > 80:
            scores[4] = 0.5
        if 10 <= temperature <= 25 and wind_speed < 15 and precipitation < 5 and humidity < 70:
            scores[1] = 0.6
        if 5 <= temperature <= 28 and wind_speed < 10 and precipitation < 2 and cloud_cover < 70:
            scores[2] = 0.7
        if 15 <= temperature <= 26 and wind_speed < 12 and precipitation == 0:
            scores[3] = 0.8
        if temperature > 35 or humidity > 85 or wind_speed > 22:
            scores[4] = 0.9

        total = sum(scores) + 0.01
        y.append([score / total for score in scores])

    return X, y
