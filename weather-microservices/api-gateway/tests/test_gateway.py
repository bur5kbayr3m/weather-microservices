import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import create_app


def test_health_endpoint():
    app = create_app()
    app.testing = True
    client = app.test_client()

    response = client.get('/health')

    assert response.status_code == 200
    assert response.json['status'] == 'ok'
