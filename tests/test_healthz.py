from fastapi.testclient import TestClient
from app.main import app


def test_healthz_returns_200_and_status_ok():
    client = TestClient(app)
    response = client.get("/healthz")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "db" in body
    assert body["db"] == "ok"
