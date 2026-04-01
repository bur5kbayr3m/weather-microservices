from app.main import create_app


def test_health_endpoint():
    app = create_app()
    app.testing = True
    client = app.test_client()

    response = client.get('/health')

    assert response.status_code == 200
    assert response.json['service'] == 'auth-service'
