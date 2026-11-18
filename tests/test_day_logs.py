from datetime import date, timedelta

from app import db
from app.seed import create_account


def test_task_time_override_round_trips_and_can_be_removed(client, account_headers):
    day = db.today_cn()
    endpoint = f"/api/day/{day}"
    task = {"id": "one", "title": "Task", "startTime": "08:13", "endTime": "09:28"}

    response = client.put(endpoint, headers=account_headers, json={"tasks": [{
        **task, "timeOverridden": True, "startTime": "24:00",
    }]})
    assert response.status_code == 400

    response = client.put(endpoint, headers=account_headers, json={"tasks": [{
        **task, "done": True, "focusSec": 90, "timeOverridden": True,
    }]})
    assert response.status_code == 200, response.text
    stored = client.get("/api/state", headers=account_headers).json()["days"][0]["tasks"][0]
    assert stored["timeOverridden"] is True
    assert (stored["startTime"], stored["endTime"], stored["done"], stored["focusSec"]) == (
        "08:13", "09:28", True, 90,
    )
    assert client.get("/api/export", headers=account_headers).json()["days"][0]["tasks"][0] == stored

    response = client.put(endpoint, headers=account_headers, json={"tasks": [{
        **stored, "startTime": "07:00", "timeOverridden": False,
    }, {"id": "legacy", "title": "Old backup task"}]})
    assert response.status_code == 200, response.text
    first, legacy = response.json()["tasks"]
    assert "timeOverridden" not in first and "timeOverridden" not in legacy
    assert (first["startTime"], first["done"], first["focusSec"]) == ("07:00", True, 90)


def test_learning_summary_counts_all_owned_days_and_only_confirmed_checkins(client, account_headers):
    today = date.fromisoformat(db.today_cn())
    owner = client.get("/api/me", headers=account_headers).json()["id"]
    with db.connect() as conn:
        other = create_account(conn, "another_user", "test-password-123")
        logs = [
            (owner, (today - timedelta(days=i)).isoformat(), 100, int(i in (1, 2, 500)), 60, db.now_iso())
            for i in range(501)
        ]
        logs.append((other, today.isoformat(), 100, 1, 900, db.now_iso()))
        conn.executemany(
            "INSERT INTO day_logs(owner_id, day, completion, checked_in, focus_sec, updated_at) VALUES(?,?,?,?,?,?)",
            logs,
        )
    assert client.get("/api/learning-summary").status_code == 401
    assert client.get("/api/learning-summary", headers=account_headers).json() == {
        "checkinDays": 3, "streak": 2, "totalFocusSec": 501 * 60,
    }
