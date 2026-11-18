from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException

from ..db import get_db, now_iso
from ..deps import current_account, extract_token
from ..schemas import LoginIn, PasswordIn
from ..security import (
    LOCK_MINUTES,
    MAX_FAILS,
    SESSION_DAYS,
    hash_password,
    hash_token,
    new_token,
    verify_password,
)
from ..serialize import account_to_user

router = APIRouter(prefix="/api", tags=["auth"])


def _iso(moment: datetime) -> str:
    return moment.isoformat(timespec="seconds")


@router.post("/login")
def login(payload: LoginIn, conn=Depends(get_db)):
    row = conn.execute(
        "SELECT * FROM accounts WHERE username=?", (payload.username.strip(),)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=401, detail="账号或密码不正确")
    if row["status"] != "active":
        raise HTTPException(status_code=403, detail="账号已被停用，请联系管理员")

    now = datetime.now(timezone.utc)
    if row["locked_until"]:
        try:
            locked_until = datetime.fromisoformat(row["locked_until"])
        except ValueError:
            locked_until = None
        if locked_until and locked_until > now:
            minutes = max(1, int((locked_until - now).total_seconds() // 60) + 1)
            raise HTTPException(
                status_code=429, detail=f"密码错误次数过多，请 {minutes} 分钟后再试"
            )

    if not verify_password(
        payload.password, row["pwd_salt"], row["pwd_hash"], row["iterations"]
    ):
        fails = row["fail_count"] + 1
        if fails >= MAX_FAILS:
            conn.execute(
                "UPDATE accounts SET fail_count=0, locked_until=? WHERE id=?",
                (_iso(now + timedelta(minutes=LOCK_MINUTES)), row["id"]),
            )
            conn.commit()
            raise HTTPException(
                status_code=429, detail=f"密码错误次数过多，请 {LOCK_MINUTES} 分钟后再试"
            )
        conn.execute(
            "UPDATE accounts SET fail_count=? WHERE id=?", (fails, row["id"])
        )
        conn.commit()
        left = MAX_FAILS - fails
        raise HTTPException(
            status_code=401, detail=f"账号或密码不正确，再错 {left} 次将锁定 {LOCK_MINUTES} 分钟"
        )

    token = new_token()
    expires = now + timedelta(days=SESSION_DAYS)
    conn.execute(
        "INSERT INTO sessions(token_hash, account_id, created_at, expires_at, last_seen)"
        " VALUES (?,?,?,?,?)",
        (hash_token(token), row["id"], _iso(now), _iso(expires), _iso(now)),
    )
    conn.execute(
        "UPDATE accounts SET fail_count=0, locked_until=NULL, last_login_at=? WHERE id=?",
        (_iso(now), row["id"]),
    )
    conn.commit()

    fresh = conn.execute("SELECT * FROM accounts WHERE id=?", (row["id"],)).fetchone()
    return {
        "token": token,
        "expiresAt": _iso(expires),
        "user": account_to_user(fresh),
    }


@router.post("/logout")
def logout(
    conn=Depends(get_db),
    authorization: str | None = Header(default=None),
    x_token: str | None = Header(default=None),
):
    token = extract_token(authorization, x_token)
    if token:
        conn.execute("DELETE FROM sessions WHERE token_hash=?", (hash_token(token),))
        conn.commit()
    return {"ok": True}


@router.get("/me")
def me(account=Depends(current_account)):
    return account_to_user(account)


@router.post("/password")
def change_password(
    payload: PasswordIn,
    account=Depends(current_account),
    conn=Depends(get_db),
    authorization: str | None = Header(default=None),
    x_token: str | None = Header(default=None),
):
    if not verify_password(
        payload.oldPassword, account["pwd_salt"], account["pwd_hash"], account["iterations"]
    ):
        raise HTTPException(status_code=400, detail="原密码不正确")
    if payload.newPassword == payload.oldPassword:
        raise HTTPException(status_code=400, detail="新密码不能与原密码相同")

    pwd_hash, salt, iterations = hash_password(payload.newPassword)
    conn.execute(
        "UPDATE accounts SET pwd_hash=?, pwd_salt=?, iterations=?, must_change_password=0"
        " WHERE id=?",
        (pwd_hash, salt, iterations, account["id"]),
    )
    current = extract_token(authorization, x_token)
    keep = hash_token(current) if current else ""
    conn.execute(
        "DELETE FROM sessions WHERE account_id=? AND token_hash<>?", (account["id"], keep)
    )
    conn.commit()
    return {"ok": True}
