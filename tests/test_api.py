import pytest


def test_event_api_create_get_update_delete(tmp_path, monkeypatch):
    fastapi = pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient
    from app.api import routes
    from app.api.main import app
    from app.memory.database import MemoryDatabase

    monkeypatch.setattr(routes, "database", MemoryDatabase(tmp_path / "api.sqlite3"))
    client = TestClient(app)
    payload = {"name":"API sample","event_type":"Birthday party","event_date":"2030-05-20","location":"Pune","guest_count":20,"budget":20000,"user_id":"api-test"}
    created = client.post("/events", json=payload)
    assert created.status_code == 201
    event_id = created.json()["event_id"]
    assert client.get(f"/events/{event_id}").json()["name"] == "API sample"
    payload["name"] = "Updated API sample"
    assert client.put(f"/events/{event_id}", json=payload).status_code == 200
    assert client.delete(f"/events/{event_id}?user_id=api-test").status_code == 204
    assert client.get(f"/events/{event_id}").status_code == 404
