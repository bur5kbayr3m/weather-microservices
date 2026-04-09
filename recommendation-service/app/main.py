"""
Recommendation Service - AI-powered weather recommendations API.
Provides REST endpoints for weather-based activity recommendations.
"""

import os
import logging
from pathlib import Path
from typing import Any
from flask import Flask, request, jsonify
from app.recommendation_engine import RecommendationService, generate_synthetic_training_data

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global recommendation service instance
recommendation_service: RecommendationService = RecommendationService()


def _has_weather_fields(weather_data: dict) -> bool:
    """Accept either generic weather keys or weather-service response keys."""
    return (
        ('temperature' in weather_data or 'temperature_c' in weather_data)
        and ('humidity' in weather_data or 'humidity_percent' in weather_data)
        and ('wind_speed' in weather_data or 'wind_speed_kmh' in weather_data)
        and ('precipitation' in weather_data or 'precipitation_mm' in weather_data)
        and ('cloud_cover' in weather_data or 'cloud_cover_percent' in weather_data)
    )


def create_app() -> Flask:
    """Create and configure Flask application."""
    app = Flask(__name__)
    
    # Configuration
    app.config['JSON_SORT_KEYS'] = False
    
    # Initialize recommendation service
    global recommendation_service
    model_path = Path(__file__).parent / 'models' / 'recommendation_model.h5'
    recommendation_service = RecommendationService(
        model_path=model_path if model_path.exists() else None
    )
    
    # Register routes
    @app.route('/health', methods=['GET'])
    def health_check():
        """Health check endpoint."""
        return jsonify({
            'status': 'healthy',
            'service': 'recommendation-service',
            'version': '1.0.0',
            'ai_model_trained': recommendation_service.model.trained
        }), 200
    
    @app.route('/api/v1/recommend', methods=['POST'])
    def get_recommendation():
        """
        Get activity recommendation based on weather.
        
        Request body:
        {
            "temperature": 20,
            "humidity": 65,
            "wind_speed": 10,
            "precipitation": 0,
            "cloud_cover": 40
        }
        """
        try:
            weather_data = request.get_json()
            
            if not weather_data:
                return jsonify({'error': 'No JSON data provided'}), 400
            
            if not _has_weather_fields(weather_data):
                return jsonify({
                    'error': 'Missing required weather fields',
                    'expected': [
                        'temperature or temperature_c',
                        'humidity or humidity_percent',
                        'wind_speed or wind_speed_kmh',
                        'precipitation or precipitation_mm',
                        'cloud_cover or cloud_cover_percent',
                    ],
                }), 400
            
            # Get recommendation
            recommendation = recommendation_service.get_recommendation(weather_data)
            
            return jsonify(recommendation), 200
        
        except ValueError as e:
            logger.error(f"Validation error: {str(e)}")
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            logger.error(f"Error getting recommendation: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @app.route('/api/v1/outfit', methods=['POST'])
    def get_outfit_recommendation():
        """Get weather-based outfit and color combination recommendations."""
        try:
            weather_data = request.get_json()

            if not weather_data:
                return jsonify({'error': 'No JSON data provided'}), 400

            if not _has_weather_fields(weather_data):
                return jsonify({
                    'error': 'Missing required weather fields',
                    'expected': [
                        'temperature or temperature_c',
                        'humidity or humidity_percent',
                        'wind_speed or wind_speed_kmh',
                        'precipitation or precipitation_mm',
                        'cloud_cover or cloud_cover_percent',
                    ],
                }), 400

            outfit = recommendation_service.get_outfit_recommendation(weather_data)
            return jsonify(outfit), 200

        except ValueError as e:
            logger.error(f"Validation error: {str(e)}")
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            logger.error(f"Error getting outfit recommendation: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/v1/recommend-batch', methods=['POST'])
    def get_batch_recommendations():
        """
        Get recommendations for multiple weather forecasts.
        
        Request body:
        {
            "forecasts": [
                {"temperature": 20, "humidity": 65, ...},
                {"temperature": 22, "humidity": 60, ...}
            ]
        }
        """
        try:
            data = request.get_json()
            
            if not data or 'forecasts' not in data:
                return jsonify({'error': 'Missing forecasts data'}), 400
            
            forecasts = data['forecasts']
            
            if not isinstance(forecasts, list):
                return jsonify({'error': 'Forecasts must be a list'}), 400
            
            recommendations = recommendation_service.get_multiple_recommendations(forecasts)
            
            return jsonify({
                'count': len(recommendations),
                'recommendations': recommendations
            }), 200
        
        except Exception as e:
            logger.error(f"Error getting batch recommendations: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/v1/history', methods=['GET'])
    def get_recommendation_history():
        """Get recent recommendation history."""
        try:
            limit = request.args.get('limit', 10, type=int)
            history = recommendation_service.get_history(limit=limit)
            
            return jsonify({
                'count': len(history),
                'recommendations': history
            }), 200
        
        except Exception as e:
            logger.error(f"Error getting history: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/v1/activities', methods=['GET'])
    def get_activities():
        """Get list of possible activity recommendations."""
        from app.recommendation_engine import WeatherRecommendationModel
        
        return jsonify({
            'activities': WeatherRecommendationModel.ACTIVITIES
        }), 200
    
    @app.route('/api/v1/train', methods=['POST'])
    def train_model():
        """
        Train the recommendation model (admin only).
        Generates synthetic data and trains the neural network.
        """
        try:
            # Check for admin token (in production, verify JWT)
            token = request.headers.get('Authorization', '')
            
            # For demo, accept any bearer token
            if not token.startswith('Bearer '):
                return jsonify({'error': 'Unauthorized'}), 401
            
            # Generate synthetic data
            logger.info("Generating synthetic training data...")
            X_train, y_train = generate_synthetic_training_data(n_samples=2000)
            
            # Split into train/val
            split_idx = int(len(X_train) * 0.8)
            X_val, y_val = X_train[split_idx:], y_train[split_idx:]
            X_train, y_train = X_train[:split_idx], y_train[:split_idx]
            
            # Train model
            logger.info("Training recommendation model...")
            history = recommendation_service.model.train(
                X_train, y_train,
                X_val, y_val,
                epochs=30,
                batch_size=32
            )
            
            # Save model
            model_dir = Path(__file__).parent / 'models'
            model_dir.mkdir(exist_ok=True)
            model_path = model_dir / 'recommendation_model.h5'
            recommendation_service.model.save_model(model_path)
            
            logger.info(f"Model saved to {model_path}")
            
            return jsonify({
                'status': 'success',
                'message': 'Model trained successfully',
                'epochs': len(history.history['loss']),
                'final_accuracy': float(history.history['accuracy'][-1])
            }), 200
        
        except Exception as e:
            logger.error(f"Error training model: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/v1/stats', methods=['GET'])
    def get_stats():
        """Get service statistics."""
        return jsonify({
            'total_recommendations': len(recommendation_service.recommendation_history),
            'model_trained': recommendation_service.model.trained,
            'model_activities': len(recommendation_service.model.ACTIVITIES)
        }), 200
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error: Any):
        return jsonify({'error': 'Not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error: Any):
        return jsonify({'error': 'Internal server error'}), 500
    
    return app


if __name__ == '__main__':
    app = create_app()
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', '5000')), debug=debug)
