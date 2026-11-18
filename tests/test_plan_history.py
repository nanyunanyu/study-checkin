def test_plan_history_archives_changed_versions_and_can_restore_them(client, account_headers):
    headers = account_headers
    original = client.get("/api/state", headers=headers).json()["plan"]
    endpoint = "/api/plan/history"
    assert client.get(endpoint, headers=headers).json() == {"versions": [], "nextBefore": None}

    changed = [dict(original[1], title="Modified task", focusMin=17, active=False), original[0]]
    response = client.put("/api/plan", headers=headers, json={"items": changed})
    assert response.status_code == 200
    current = response.json()["plan"]
    assert [item["id"] for item in current] == [item["id"] for item in changed]
    versions = client.get(endpoint, headers=headers).json()["versions"]
    version = versions[0]
    assert version["itemCount"] == len(original)
    snapshot_url = f"{endpoint}/{version['id']}"
    assert client.get(snapshot_url, headers=headers).json() == {"items": original}
    assert client.get("/api/state", headers=headers).json()["plan"] == current

    assert client.put("/api/plan", headers=headers, json={"items": current}).status_code == 200
    assert client.get(endpoint, headers=headers).json()["versions"] == [version]

    response = client.put("/api/plan", headers=headers, json={"items": original})
    assert response.json()["plan"] == original
    versions = client.get(endpoint, headers=headers).json()["versions"]
    assert versions[1:] == [version]
    assert client.get(f"{endpoint}/{versions[0]['id']}", headers=headers).json() == {"items": current}


def test_plan_history_is_account_scoped_and_archives_category_renames(client, account_headers):
    headers = account_headers
    created = client.post(
        "/api/admin/users", headers=headers,
        json={"username": "otheruser", "password": "test-password-123"},
    )
    assert created.status_code == 200
    login = client.post("/api/login", json={"username": "otheruser", "password": "test-password-123"})
    other = {"X-Token": login.json()["token"]}

    item = {"id": "custom-task", "title": "Practice", "subject": "Programming"}
    assert client.put("/api/plan", headers=headers, json={"items": [item]}).status_code == 200
    category = client.get("/api/categories", headers=headers).json()["custom"][0]
    rename = client.patch(f"/api/categories/{category['id']}", headers=headers, json={"name": "Development"})
    assert rename.status_code == 200

    endpoint = "/api/plan/history"
    versions = client.get(endpoint, headers=headers).json()["versions"]
    assert len(versions) == 2
    snapshot_url = f"{endpoint}/{versions[0]['id']}"
    assert client.get(snapshot_url, headers=headers).json()["items"][0]["subject"] == "Programming"
    assert client.get(endpoint, headers=other).json()["versions"] == []
    assert client.get(snapshot_url, headers=other).status_code == 404
    assert client.get(endpoint).status_code == 401
