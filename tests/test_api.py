from fastapi.testclient import TestClient

from domainwatch.api.app import app

client = TestClient(app)


def test_root():
    r = client.get("/")
    assert r.status_code == 200 and r.json()["service"] == "DomainWatch"


def test_providers():
    r = client.get("/providers")
    assert "godaddy" in r.json()["providers"]


def test_dns():
    r = client.get("/dns/example.com")
    assert r.status_code == 200
