import json
import re
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException

from ..db import backup_snapshot, ensure_plan_categories, get_db, now_iso, today_cn
from ..deps import current_account
from ..plan import archive_plan, load_plan
from ..schemas import DayIn, PlanIn
from ..serialize import day_row_to_log

router = APIRouter(prefix="/api", tags=["data"])

DAY_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TIME_PATTERN = re.compile(r"^$|^([01]\d|2[0-3]):[0-5]\d$")


def _check_day(day: str) -> str:
    if not DAY_PATTERN.match(day or ""):
        raise HTTPException(status_code=400, detail="日期格式应为 YYYY-MM-DD")
    try:
        datetime.strptime(day, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="日期不合法")
    return day


def load_days(conn, owner_id: int, limit: int = 500) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM day_logs WHERE owner_id=? ORDER BY day DESC LIMIT ?",
        (owner_id, limit),
    ).fetchall()
    return [day_row_to_log(row) for row in reversed(rows)]


@router.get("/state")
def get_state(account=Depends(current_account), conn=Depends(get_db)):
    owner_id = account["id"]
    return {
        "user": {
            "id": account["id"],
            "username": account["username"],
            "displayName": account["display_name"] or "",
            "role": account["role"],
            "mustChangePassword": bool(account["must_change_password"]),
        },
        "plan": load_plan(conn, owner_id),
        "days": load_days(conn, owner_id),
    }


@router.get("/plan/template")
def plan_template(account=Depends(current_account)):
    from ..seed import template_items

    return {"items": template_items()}


@router.get("/plan/history")
def plan_history(before: int | None = None, account=Depends(current_account), conn=Depends(get_db)):
    limit = 30
    owner_id = account["id"]
    rows = conn.execute(
        "SELECT id, replaced_at, item_count FROM plan_history WHERE owner_id=?"
        " AND (? IS NULL OR id < ?) ORDER BY id DESC LIMIT ?",
        (owner_id, before, before, limit + 1),
    ).fetchall()
    return {
        "versions": [
            {"id": row["id"], "replacedAt": row["replaced_at"], "itemCount": row["item_count"]}
            for row in rows[:limit]
        ],
        "nextBefore": rows[limit - 1]["id"] if len(rows) > limit else None,
    }


@router.get("/plan/history/{version_id}")
def plan_version(version_id: int, account=Depends(current_account), conn=Depends(get_db)):
    row = conn.execute(
        "SELECT items FROM plan_history WHERE id=? AND owner_id=?", (version_id, account["id"])
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="历史计划不存在")
    return {"items": json.loads(row["items"])}


def learning_stats(conn, owner_id: int) -> dict:
    rows = conn.execute(
        "SELECT day, completion, checked_in, focus_sec FROM day_logs WHERE owner_id=?",
        (owner_id,),
    ).fetchall()
    today = today_cn()
    today_row = next((row for row in rows if row["day"] == today), None)
    checked = {row["day"] for row in rows if row["checked_in"]}
    cursor = datetime.strptime(today, "%Y-%m-%d").date()
    if today not in checked:
        cursor -= timedelta(days=1)
    streak = 0
    while cursor.isoformat() in checked:
        streak += 1
        cursor -= timedelta(days=1)
    return {
        "todayCompletion": float(today_row["completion"]) if today_row else 0.0,
        "todayCheckedIn": bool(today_row["checked_in"]) if today_row else False,
        "streak": streak,
        "checkinDays": len(checked),
        "totalFocusSec": sum(int(row["focus_sec"] or 0) for row in rows),
    }


@router.get("/learning-summary")
def learning_summary(account=Depends(current_account), conn=Depends(get_db)):
    stats = learning_stats(conn, account["id"])
    return {key: stats[key] for key in ("streak", "checkinDays", "totalFocusSec")}


@router.put("/plan")
def save_plan(
    payload: PlanIn, account=Depends(current_account), conn=Depends(get_db)
):
    owner_id = account["id"]
    if len(payload.items) > 200:
        raise HTTPException(status_code=400, detail="计划条目过多（上限 200 条）")

    seen = set()
    for item in payload.items:
        if not TIME_PATTERN.match(item.startTime or "") or not TIME_PATTERN.match(
            item.endTime or ""
        ):
            raise HTTPException(status_code=400, detail=f"时间格式不合法：{item.title}")
        if item.id in seen:
            raise HTTPException(status_code=400, detail="计划条目 id 重复")
        seen.add(item.id)

    conn.execute("BEGIN IMMEDIATE")
    previous = load_plan(conn, owner_id)
    ensure_plan_categories(conn, owner_id, (item.subject for item in payload.items))

    conn.execute("DELETE FROM plan_items WHERE owner_id=?", (owner_id,))
    conn.executemany(
        "INSERT INTO plan_items(owner_id, id, sort_order, start_time, end_time, title, subject, focus_min, note, active)"
        " VALUES (?,?,?,?,?,?,?,?,?,?)",
        [
            (
                owner_id,
                item.id,
                index,
                item.startTime,
                item.endTime,
                item.title.strip(),
                item.subject or "其他",
                max(1, min(600, item.focusMin)) if item.focusMin is not None else None,
                item.note or "",
                1 if item.active else 0,
            )
            for index, item in enumerate(payload.items)
        ],
    )
    saved = load_plan(conn, owner_id)
    if saved != previous:
        archive_plan(conn, owner_id, previous)
    conn.commit()
    return {"plan": saved}


@router.put("/day/{day}")
def save_day(
    day: str, payload: DayIn, account=Depends(current_account), conn=Depends(get_db)
):
    day = _check_day(day)
    owner_id = account["id"]

    tasks = []
    for task in payload.tasks:
        if task.timeOverridden and not all(
            TIME_PATTERN.fullmatch(value) for value in (task.startTime, task.endTime)
        ):
            raise HTTPException(status_code=400, detail="时间格式应为 HH:mm")
        tasks.append(
            {
                "id": task.id,
                "startTime": task.startTime,
                "endTime": task.endTime,
                **({"timeOverridden": True} if task.timeOverridden else {}),
                "title": task.title,
                "subject": task.subject or "其他",
                "note": task.note or "",
                "done": bool(task.done),
                "focusSec": max(0, int(task.focusSec or 0)),
            }
        )

    total = len(tasks)
    done = sum(1 for task in tasks if task["done"])
    completion = round(done / total * 100, 1) if total else 0.0
    # 绑定任务的专注会计入任务；未绑定任务的专注只记在当天，不能因此被覆盖掉
    focus_sec = max(sum(task["focusSec"] for task in tasks), max(0, int(payload.focusSec or 0)))
    # 打卡是用户主动确认的独立动作，不随任务勾选自动发生
    checked_in = 1 if payload.checkedIn else 0

    conn.execute(
        "INSERT INTO day_logs(owner_id, day, tasks, review, focus_sec, completion, checked_in, updated_at)"
        " VALUES (?,?,?,?,?,?,?,?)"
        " ON CONFLICT(owner_id, day) DO UPDATE SET"
        " tasks=excluded.tasks, review=excluded.review, focus_sec=excluded.focus_sec,"
        " completion=excluded.completion, checked_in=excluded.checked_in, updated_at=excluded.updated_at",
        (
            owner_id,
            day,
            json.dumps(tasks, ensure_ascii=False),
            json.dumps(payload.review or {}, ensure_ascii=False),
            focus_sec,
            completion,
            checked_in,
            now_iso(),
        ),
    )
    conn.commit()
    backup_snapshot()

    row = conn.execute(
        "SELECT * FROM day_logs WHERE owner_id=? AND day=?", (owner_id, day)
    ).fetchone()
    return day_row_to_log(row)


@router.get("/export")
def export_data(account=Depends(current_account), conn=Depends(get_db)):
    owner_id = account["id"]
    categories = conn.execute(
        "SELECT name FROM plan_categories WHERE owner_id=? ORDER BY id ASC", (owner_id,)
    ).fetchall()
    return {
        "exportedAt": now_iso(),
        "username": account["username"],
        "plan": load_plan(conn, owner_id),
        "days": load_days(conn, owner_id, limit=5000),
        "categories": [row["name"] for row in categories],
    }
