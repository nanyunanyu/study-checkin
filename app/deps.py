from datetime import datetime, timedelta, timezone

from fastapi import Depends, Header, HTTPException

from .db import get_db, now_iso
from .security import SESSION_DAYS, hash_token


def _unauthorized(detail: str = "登录已失效，请重新登录") -> HTTPException:
    return HTTPException(status_code=401, detail=detail)


def extract_token(authorization: str | None, x_token: str | None) -> str:
    """取会话令牌。

    优先读自定义头 X-Token：托管平台的网关会用自己的 JWT 覆盖 Authorization，
    只认 Authorization 会永远认证失败。Authorization 仅作为本地直连时的兼容。
    """
    if x_token and x_token.strip():
        return x_token.strip()
    if authorization and authorization.lower().startswith("bearer "):
        return authorization.split(" ", 1)[1].strip()
    return ""


def current_account(
    conn=Depends(get_db),
    authorization: str | None = Header(default=None),
    x_token: str | None = Header(default=None),
):
    token = extract_token(authorization, x_token)
    if not token:
        raise _unauthorized("未登录")
    token_hash = hash_token(token)

    sess = conn.execute(
        "SELECT account_id, expires_at FROM sessions WHERE token_hash=?", (token_hash,)
    ).fetchone()
    if sess is None:
        raise _unauthorized()

    now = datetime.now(timezone.utc)
    try:
        expires = datetime.fromisoformat(sess["expires_at"])
    except ValueError:
        expires = now
    if expires <= now:
        conn.execute("DELETE FROM sessions WHERE token_hash=?", (token_hash,))
        conn.commit()
        raise _unauthorized("登录已过期，请重新登录")

    account = conn.execute("SELECT * FROM accounts WHERE id=?", (sess["account_id"],)).fetchone()
    if account is None:
        conn.execute("DELETE FROM sessions WHERE token_hash=?", (token_hash,))
        conn.commit()
        raise _unauthorized()
    if account["status"] != "active":
        raise HTTPException(status_code=403, detail="账号已被停用，请联系管理员")

    if expires - now < timedelta(days=SESSION_DAYS - 1):
        conn.execute(
            "UPDATE sessions SET expires_at=?, last_seen=? WHERE token_hash=?",
            (
                (now + timedelta(days=SESSION_DAYS)).isoformat(timespec="seconds"),
                now_iso(),
                token_hash,
            ),
        )
        conn.commit()

    return account


def require_superadmin(account=Depends(current_account)):
    if account["role"] != "superadmin":
        raise HTTPException(status_code=403, detail="仅超级管理员可以执行该操作")
    return account
