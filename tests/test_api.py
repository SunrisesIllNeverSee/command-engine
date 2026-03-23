"""
Tests for the REST API — verifies the server starts and key endpoints respond correctly.
"""
from fastapi.testclient import TestClient

from app.server import create_app


def test_state_returns_valid_structure(runtime_root):
    client = TestClient(create_app(runtime_root))
    response = client.get("/api/state")
    assert response.status_code == 200
    data = response.json()
    assert "governance" in data
    assert "systems" in data
    assert "vault" in data


def test_governance_update(runtime_root):
    client = TestClient(create_app(runtime_root))
    response = client.post("/api/governance", json={"mode": "RESEARCH", "posture": "SCOUT"})
    assert response.status_code == 200

    state = client.get("/api/state").json()
    assert state["governance"]["mode"] == "RESEARCH"
    assert state["governance"]["posture"] == "SCOUT"


def test_hash_endpoint(runtime_root):
    client = TestClient(create_app(runtime_root))
    response = client.get("/api/hash")
    assert response.status_code == 200
    data = response.json()
    assert "state_hash" in data
    assert "onchain_hash" in data
    assert data["onchain_hash"].startswith("MOSES|")


def test_audit_endpoint_returns_list(runtime_root):
    client = TestClient(create_app(runtime_root))
    response = client.get("/api/audit")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
