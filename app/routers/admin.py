import re
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException

from ..db import get_db, now_iso, today_cn
from ..deps import require_superadmin
from ..schemas import ResetPasswordIn, UserCreateIn, UserPatchIn
from ..security import hash_password
from ..seed import copy_default_plan
from ..serialize import account_to_user
from .data import load_days, load_plan

router = APIRouter(prefix="/api/admin", tags=["admin"])

USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_.\-]{4,32}$")


def _audit(conn, actor_id: int, action: str, target_id: int | None, detail: str = ""):
    conn.execute(
        "INSERT INTO audit_log(actor_id, action, target_id, detail, created_at) VALUES (?,?,?,?,?)",
        (actor_id, action, target_id, detail, now_iso()),
    )


def _stats(conn, owner_id: int) -> dict:
    rows = conn.execute(
        "SELECT day, completion, checked_in, focus_sec FROM day_logs WHERE owner_id=?",
        (owner_id,),
    ).fetchall()
    by_day = {row["day"]: row for row in rows}
    checked = {row["day"] for row in rows if row["checked_in"]}

    today = today_cn()
    cursor = datetime.strptime(today, "%Y-%m-%d").date()
    if today not in checked:
        cursor -= timedelta(days=1)
    streak = 0
    while cursor.isoformat() in checked:
        streak += 1
        cursor -= timedelta(days=1)

    today_row = by_day.get(today)
    return {
        "todayCompletion": float(today_row["completion"]) if today_row else 0.0,
        "todayCheckedIn": bool(today_row["checked_in"]) if today_row else False,
        "streak": streak,
        "checkinDays": len(checked),
        "totalFocusSec": sum(int(row["focus_sec"] or 0) for row in rows),
    }


def _get_account(conn, account_id: int):
    row = conn.execute("SELECT * FROM accounts WHERE id=?", (account_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="账号不存在")
    return row


@router.get("/users")
def list_users(admin=Depends(require_superadmin), conn=Depends(get_db)):
    rows = conn.execute(
        "SELECT * FROM accounts ORDER BY (role='superadmin') DESC, id ASC"
    ).fetchall()
    users = []
    for row in rows:
        item = account_to_user(row)
        item.update(_stats(conn, row["id"]))
        users.append(item)
    return {"users": users}


@router.post("/users")
def create_user(
    payload: UserCreateIn, admin=Depends(require_superadmin), conn=Depends(get_db)
):
    username = payload.username.strip()
    if not USERNAME_PATTERN.match(username):
        raise HTTPException(
            status_code=400, detail="用户名需为 4–32 位字母、数字、下划线、点或短横线"
        )
    exists = conn.execute(
        "SELECT 1 FROM accounts WHERE username=?", (username,)
    ).fetchone()
    if exists:
        raise HTTPException(status_code=409, detail="该用户名已存在")

    pwd_hash, salt, iterations = hash_password(payload.password)
    cur = conn.execute(
        "INSERT INTO accounts(username, display_name, role, status, pwd_hash, pwd_salt,"
        " iterations, must_change_password, created_at, created_by)"
        " VALUES (?,?,'user','active',?,?,?,?,?,?)",
        (
            username,
            (payload.displayName or "").strip() or username,
            pwd_hash,
            salt,
            iterations,
            1 if payload.mustChangePassword else 0,
            now_iso(),
            admin["id"],
        ),
    )
    new_id = cur.lastrowid
    copy_default_plan(conn, new_id)
    _audit(conn, admin["id"], "create_user", new_id, username)
    conn.commit()
    return account_to_user(_get_account(conn, new_id))


@router.patch("/users/{account_id}")
def update_user(
    account_id: int,
    payload: UserPatchIn,
    admin=Depends(require_superadmin),
    conn=Depends(get_db),
):
    target = _get_account(conn, account_id)

    if payload.displayName is not None:
        conn.execute(
            "UPDATE accounts SET display_name=? WHERE id=?",
            (payload.displayName.strip()[:40], account_id),
        )

    if payload.status is not None:
        if payload.status not in ("active", "disabled"):
            raise HTTPException(status_code=400, detail="状态不合法")
        if account_id == admin["id"] and payload.status == "disabled":
            raise HTTPException(status_code=400, detail="不能停用自己的账号")
        conn.execute(
            "UPDATE accounts SET status=? WHERE id=?", (payload.status, account_id)
        )
        if payload.status == "disabled":
            conn.execute("DELETE FROM sessions WHERE account_id=?", (account_id,))
        _audit(conn, admin["id"], "set_status", account_id, payload.status)

    if payload.role is not None:
        if payload.role not in ("superadmin", "user"):
            raise HTTPException(status_code=400, detail="角色不合法")
        if target["role"] == "superadmin" and payload.role != "superadmin":
            if account_id == admin["id"]:
                raise HTTPException(status_code=400, detail="不能降级自己的超级管理员身份")
            count = conn.execute(
                "SELECT COUNT(*) AS c FROM accounts WHERE role='superadmin'"
            ).fetchone()["c"]
            if count <= 1:
                raise HTTPException(status_code=400, detail="至少需要保留一个超级管理员")
        conn.execute("UPDATE accounts SET role=? WHERE id=?", (payload.role, account_id))
        _audit(conn, admin["id"], "set_role", account_id, payload.role)

    conn.commit()
    return account_to_user(_get_account(conn, account_id))


@router.post("/users/{account_id}/password")
def reset_password(
    account_id: int,
    payload: ResetPasswordIn,
    admin=Depends(require_superadmin),
    conn=Depends(get_db),
):
    _get_account(conn, account_id)
    pwd_hash, salt, iterations = hash_password(payload.newPassword)
    conn.execute(
        "UPDATE accounts SET pwd_hash=?, pwd_salt=?, iterations=?, must_change_password=?,"
        " fail_count=0, locked_until=NULL WHERE id=?",
        (pwd_hash, salt, iterations, 1 if payload.mustChangePassword else 0, account_id),
    )
    conn.execute("DELETE FROM sessions WHERE account_id=?", (account_id,))
    _audit(conn, admin["id"], "reset_password", account_id)
    conn.commit()
    return {"ok": True}


@router.delete("/users/{account_id}")
def delete_user(
    account_id: int, admin=Depends(require_superadmin), conn=Depends(get_db)
):
    target = _get_account(conn, account_id)
    if account_id == admin["id"]:
        raise HTTPException(status_code=400, detail="不能删除自己的账号")
    if target["role"] == "superadmin":
        count = conn.execute(
            "SELECT COUNT(*) AS c FROM accounts WHERE role='superadmin'"
        ).fetchone()["c"]
        if count <= 1:
            raise HTTPException(status_code=400, detail="至少需要保留一个超级管理员")

    conn.execute("DELETE FROM day_logs WHERE owner_id=?", (account_id,))
    conn.execute("DELETE FROM plan_items WHERE owner_id=?", (account_id,))
    conn.execute("DELETE FROM sessions WHERE account_id=?", (account_id,))
    conn.execute("DELETE FROM accounts WHERE id=?", (account_id,))
    _audit(conn, admin["id"], "delete_user", account_id, target["username"])
    conn.commit()
    return {"ok": True}


@router.get("/users/{account_id}/overview")
def user_overview(
    account_id: int, admin=Depends(require_superadmin), conn=Depends(get_db)
):
    target = _get_account(conn, account_id)
    return {
        "user": account_to_user(target),
        "stats": _stats(conn, account_id),
        "plan": load_plan(conn, account_id),
        "days": load_days(conn, account_id),
        "readonly": True,
    }
