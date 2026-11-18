import json

import pytest
from fastapi.testclient import TestClient

from app import db
from app.main import app
from app.seed import create_account


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


def login(client, username="testadmin"):
    response = client.post(
        "/api/login", json={"username": username, "password": "test-password-123"}
    )
    assert response.status_code == 200, response.text
    return {"X-Token": response.json()["token"]}


def second_account(client, headers):
    response = client.post(
        "/api/admin/users", headers=headers,
        json={"username": "otheruser", "password": "test-password-123"},
    )
    assert response.status_code == 200, response.text
    return login(client, "otheruser")


def custom(client, headers):
    response = client.get("/api/categories", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()["custom"]


def save_plan(client, headers, subject):
    response = client.put(
        "/api/plan", headers=headers,
        json={"items": [{"id": "test-item", "title": "练习", "subject": subject}]},
    )
    assert response.status_code == 200, response.text


def test_categories_are_private_and_case_insensitive(client):
    headers = login(client)
    other = second_account(client, headers)
    created = client.post("/api/categories", headers=headers, json={"name": " Reading "})
    assert created.status_code == 201
    assert created.json()["name"] == "Reading"
    assert custom(client, other) == []
    assert client.post("/api/categories", headers=headers, json={"name": "reading"}).status_code == 409
    assert client.post("/api/categories", headers=headers, json={"name": "英语"}).status_code == 409
    assert client.post("/api/categories", headers=headers, json={"name": "  "}).status_code == 400
    assert client.post("/api/categories", headers=other, json={"name": "Reading"}).status_code == 201
    category_id = created.json()["id"]
    assert client.patch(f"/api/categories/{category_id}", headers=other, json={"name": "其他分类"}).status_code == 404
    assert client.delete(f"/api/categories/{category_id}", headers=other).status_code == 404


def test_rename_updates_plan_but_preserves_history_and_other_accounts(client):
    headers = login(client)
    other = second_account(client, headers)
    save_plan(client, headers, "编程")
    save_plan(client, other, "编程")
    original_day = {"tasks": [{"id": "old-task", "title": "旧任务", "subject": "编程"}]}
    assert client.put("/api/day/2026-11-17", headers=headers, json=original_day).status_code == 200
    category_id = custom(client, headers)[0]["id"]
    assert client.delete(f"/api/categories/{category_id}", headers=headers).status_code == 409
    renamed = client.patch(f"/api/categories/{category_id}", headers=headers, json={"name": "开发"})
    assert renamed.status_code == 200
    state = client.get("/api/state", headers=headers).json()
    assert state["plan"][0]["subject"] == "开发"
    assert state["days"][0]["tasks"][0]["subject"] == "编程"
    assert client.get("/api/state", headers=other).json()["plan"][0]["subject"] == "编程"
    # Editing an old snapshot must not resurrect a renamed category.
    assert client.put("/api/day/2026-11-17", headers=headers, json=original_day).status_code == 200
    assert [item["name"] for item in custom(client, headers)] == ["开发"]


def test_rename_conflict_does_not_modify_plan(client):
    headers = login(client)
    save_plan(client, headers, "Reading")
    client.post("/api/categories", headers=headers, json={"name": "Writing"})
    category_id = custom(client, headers)[0]["id"]
    response = client.patch(f"/api/categories/{category_id}", headers=headers, json={"name": "writing"})
    assert response.status_code == 409
    assert client.get("/api/state", headers=headers).json()["plan"][0]["subject"] == "Reading"


def test_old_plan_and_history_categories_migrate_once(isolated_db):
    conn = db.connect()
    try:
        conn.executescript(db.SCHEMA)
        owner = create_account(conn, "legacyuser", "test-password-123")
        other = create_account(conn, "otheruser", "test-password-123")
        conn.execute("UPDATE plan_items SET subject='旧计划分类' WHERE owner_id=?", (owner,))
        history = json.dumps([{"subject": "仅历史分类"}, {"subject": "英语"}], ensure_ascii=False)
        conn.execute(
            "INSERT INTO day_logs(owner_id, day, tasks, updated_at) VALUES (?,?,?,?)",
            (owner, "2026-11-17", history, db.now_iso()),
        )
        conn.execute(
            "INSERT INTO day_logs(owner_id, day, tasks, updated_at) VALUES (?,?,?,?)",
            (other, "2026-11-17", "broken-json", db.now_iso()),
        )
        conn.commit()
    finally:
        conn.close()

    db.init_db()
    conn = db.connect()
    try:
        names = {row["name"] for row in conn.execute("SELECT name FROM plan_categories WHERE owner_id=?", (owner,))}
        assert names == {"旧计划分类", "仅历史分类"}
        assert conn.execute("SELECT count(*) FROM plan_categories WHERE owner_id=?", (other,)).fetchone()[0] == 0
        assert conn.execute("SELECT tasks FROM day_logs WHERE owner_id=?", (owner,)).fetchone()[0] == history
        conn.execute("DELETE FROM plan_categories WHERE owner_id=? AND name='仅历史分类'", (owner,))
        conn.commit()
    finally:
        conn.close()

    db.init_db()
    conn = db.connect()
    try:
        assert not conn.execute("SELECT 1 FROM plan_categories WHERE name='仅历史分类'").fetchone()
    finally:
        conn.close()


def test_import_and_export_merge_categories_without_presets(client):
    headers = login(client)
    other = second_account(client, headers)
    response = client.post("/api/categories/import", headers=headers, json={"names": ["历史课程", "英语", "历史课程", " "]})
    assert response.status_code == 200
    assert [item["name"] for item in response.json()["custom"]] == ["历史课程"]
    assert client.get("/api/export", headers=headers).json()["categories"] == ["历史课程"]
    assert client.get("/api/export", headers=other).json()["categories"] == []
    category_id = response.json()["custom"][0]["id"]
    assert client.delete(f"/api/categories/{category_id}", headers=headers).status_code == 200
    assert custom(client, headers) == []


def test_deleting_an_account_cleans_only_its_categories(client):
    headers = login(client)
    other = second_account(client, headers)
    client.post("/api/categories", headers=headers, json={"name": "保留分类"})
    client.post("/api/categories", headers=other, json={"name": "删除分类"})
    other_id = client.get("/api/me", headers=other).json()["id"]
    assert client.delete(f"/api/admin/users/{other_id}", headers=headers).status_code == 200
    conn = db.connect()
    try:
        assert not conn.execute("SELECT 1 FROM plan_categories WHERE owner_id=?", (other_id,)).fetchone()
    finally:
        conn.close()
    assert [item["name"] for item in custom(client, headers)] == ["保留分类"]
