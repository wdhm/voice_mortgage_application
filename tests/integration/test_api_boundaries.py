from fastapi.testclient import TestClient

from app.domain.repository import repository
from app.main import app


client = TestClient(app)


def setup_function():
    repository.reset()


def test_health_endpoints_return_direct_success():
    health = client.get("/healthz")
    ready = client.get("/readyz")

    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
    assert ready.status_code == 200
    assert ready.json() == {"status": "ready"}
    assert not health.history


def test_customer_cannot_call_service_mutations():
    assert client.post("/api/customer/reset").status_code == 404
    assert client.post("/api/customer/documents/approve", json={}).status_code == 404
    assert client.post("/api/customer/documents/reject").status_code == 404


def test_customer_case_has_no_internal_fields():
    body = client.get("/api/customer/case").json()

    assert set(body) == {"customer_name", "identity_status", "document", "transcript", "meeting", "card"}
    assert "credit_result" not in body
    assert "events" not in body


def test_voice_socket_reports_missing_configuration(monkeypatch):
    monkeypatch.delenv("AZURE_VOICELIVE_ENDPOINT", raising=False)

    with client.websocket_connect("/ws/voice") as socket:
        assert socket.receive_json() == {
            "type": "voice.error",
            "message": "AZURE_VOICELIVE_ENDPOINT is not configured",
        }