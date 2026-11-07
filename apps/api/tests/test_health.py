from fastapi.testclient import TestClient


def test_live(client: TestClient) -> None:
    r = client.get("/api/v1/health/live")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_ready_checks_database(client: TestClient) -> None:
    r = client.get("/api/v1/health/ready")
    assert r.status_code == 200
    assert r.json()["database"] == "ok"


def test_request_id_is_generated_and_echoed(client: TestClient) -> None:
    r = client.get("/api/v1/health/live")
    assert len(r.headers["X-Request-ID"]) == 32

    r = client.get("/api/v1/health/live", headers={"X-Request-ID": "trace-abc-123"})
    assert r.headers["X-Request-ID"] == "trace-abc-123"


def test_malformed_request_id_is_replaced(client: TestClient) -> None:
    r = client.get("/api/v1/health/live", headers={"X-Request-ID": "bad id\nwith newline"})
    assert r.headers["X-Request-ID"] != "bad id\nwith newline"


def test_unknown_route_uses_error_envelope(client: TestClient) -> None:
    r = client.get("/api/v1/does-not-exist")
    assert r.status_code == 404
    body = r.json()["error"]
    assert body["code"] == "not_found"
    assert body["request_id"] == r.headers["X-Request-ID"]
