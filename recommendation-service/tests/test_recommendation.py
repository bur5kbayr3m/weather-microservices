"""Tests for recommendation service."""

import sys
from pathlib import Path
from typing import cast

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'app'))

import pytest
from flask import Flask
from flask.testing import FlaskClient
from main import create_app  # type: ignore[import-not-found]


@pytest.fixture
def app() -> Flask:
    """Create app for testing."""
    app = cast(Flask, create_app())
    app.config['TESTING'] = True
    return app


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    """Create test client."""
    return app.test_client()


def test_health_endpoint(client: FlaskClient):
    """Test health check endpoint."""
    response = client.get('/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'healthy'
    assert data['service'] == 'recommendation-service'


def test_get_recommendation(client: FlaskClient):
    """Test recommendation endpoint."""
    weather_data = {
        'temperature': 20,
        'humidity': 65,
        'wind_speed': 10,
        'precipitation': 0,
        'cloud_cover': 40
    }
    
    response = client.post('/api/v1/recommend', json=weather_data)
    assert response.status_code == 200
    data = response.get_json()
    
    assert 'primary_recommendation' in data
    assert 'alternatives' in data
    assert 'weather_summary' in data
    
    primary = data['primary_recommendation']
    assert 'activity' in primary
    assert 'confidence' in primary
    assert 'reasoning' in primary


def test_get_outfit_recommendation(client: FlaskClient):
    """Test outfit recommendation endpoint."""
    weather_data = {
        'temperature_c': 18,
        'humidity_percent': 68,
        'wind_speed_kmh': 12,
        'precipitation_mm': 0,
        'cloud_cover_percent': 35,
    }

    response = client.post('/api/v1/outfit', json=weather_data)
    assert response.status_code == 200
    data = response.get_json()

    assert 'title' in data
    assert 'colors' in data
    assert 'pieces' in data
    assert 'weather_note' in data


def test_recommendations_missing_fields(client: FlaskClient):
    """Test recommendation with missing fields."""
    weather_data = {'temperature': 20}
    
    response = client.post('/api/v1/recommend', json=weather_data)
    assert response.status_code == 400


def test_batch_recommendations(client: FlaskClient):
    """Test batch recommendation endpoint."""
    forecasts = [
        {
            'temperature': 20,
            'humidity': 65,
            'wind_speed': 10,
            'precipitation': 0,
            'cloud_cover': 40
        },
        {
            'temperature': 5,
            'humidity': 80,
            'wind_speed': 20,
            'precipitation': 10,
            'cloud_cover': 90
        }
    ]
    
    response = client.post('/api/v1/recommend-batch', json={'forecasts': forecasts})
    assert response.status_code == 200
    data = response.get_json()
    assert data['count'] == 2


def test_activities_endpoint(client: FlaskClient):
    """Test activities listing endpoint."""
    response = client.get('/api/v1/activities')
    assert response.status_code == 200
    data = response.get_json()
    assert 'activities' in data
    assert len(data['activities']) == 5


def test_stats_endpoint(client: FlaskClient):
    """Test stats endpoint."""
    response = client.get('/api/v1/stats')
    assert response.status_code == 200
    data = response.get_json()
    assert 'total_recommendations' in data
    assert 'model_trained' in data


def test_history_endpoint(client: FlaskClient):
    """Test history endpoint."""
    # Add some recommendations first
    weather_data = {
        'temperature': 20,
        'humidity': 65,
        'wind_speed': 10,
        'precipitation': 0,
        'cloud_cover': 40
    }
    
    client.post('/api/v1/recommend', json=weather_data)
    
    # Get history
    response = client.get('/api/v1/history?limit=5')
    assert response.status_code == 200
    data = response.get_json()
    assert 'count' in data
    assert 'recommendations' in data


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
