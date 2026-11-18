import pytest
from fastapi.testclient import TestClient

from app import db
from app.main import app


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATA_DIR", tmp_path)
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "study.db")
    monkeypatch.setattr(db, "BACKUP_DIR", tmp_path / "backups")
    monkeypatch.setattr(db, "_backup_state", {"day": None})
    monkeypatch.setenv("STUDY_ADMIN_USERNAME", "testadmin")
    monkeypatch.setenv("STUDY_ADMIN_PASSWORD", "test-password-123")


@pytest.fixture
def client(isolated_db):
    with TestClient(app) as client:
        yield client


@pytest.fixture
def account_headers(client):
    response = client.post(
        "/api/login", json={"username": "testadmin", "password": "test-password-123"}
    )
    assert response.status_code == 200, response.text
    return {"X-Token": response.json()["token"]}
