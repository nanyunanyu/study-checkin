import json


def plan_row_to_item(row) -> dict:
    return {
        "id": row["id"],
        "sortOrder": row["sort_order"],
        "startTime": row["start_time"] or "",
        "endTime": row["end_time"] or "",
        "title": row["title"],
        "subject": row["subject"] or "其他",
        "focusMin": row["focus_min"],
        "note": row["note"] or "",
        "active": bool(row["active"]),
    }


def day_row_to_log(row) -> dict:
    try:
        tasks = json.loads(row["tasks"] or "[]")
    except ValueError:
        tasks = []
    try:
        review = json.loads(row["review"] or "{}")
    except ValueError:
        review = {}
    return {
        "day": row["day"],
        "tasks": tasks,
        "review": review,
        "focusSec": row["focus_sec"],
        "completion": row["completion"],
        "checkedIn": bool(row["checked_in"]),
        "updatedAt": row["updated_at"],
    }


def account_to_user(row) -> dict:
    return {
        "id": row["id"],
        "username": row["username"],
        "displayName": row["display_name"] or "",
        "role": row["role"],
        "status": row["status"],
        "mustChangePassword": bool(row["must_change_password"]),
        "createdAt": row["created_at"],
        "lastLoginAt": row["last_login_at"],
    }
