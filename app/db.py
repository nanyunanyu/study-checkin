import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("DATA_DIR") or (BASE_DIR / "data"))
DB_PATH = DATA_DIR / "study.db"
BACKUP_DIR = DATA_DIR / "backups"

CN_TZ = timezone(timedelta(hours=8))

SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT NOT NULL UNIQUE,
  display_name TEXT,
  role TEXT NOT NULL DEFAULT 'user',
  status TEXT NOT NULL DEFAULT 'active',
  pwd_hash TEXT NOT NULL,
  pwd_salt TEXT NOT NULL,
  iterations INTEGER NOT NULL DEFAULT 120000,
  must_change_password INTEGER NOT NULL DEFAULT 0,
  fail_count INTEGER NOT NULL DEFAULT 0,
  locked_until TEXT,
  created_at TEXT NOT NULL,
  created_by INTEGER,
  last_login_at TEXT
);

CREATE TABLE IF NOT EXISTS sessions (
  token_hash TEXT PRIMARY KEY,
  account_id INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  last_seen TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sessions_account ON sessions(account_id);

CREATE TABLE IF NOT EXISTS plan_items (
  owner_id INTEGER NOT NULL,
  id TEXT NOT NULL,
  sort_order INTEGER NOT NULL,
  start_time TEXT,
  end_time TEXT,
  title TEXT NOT NULL,
  subject TEXT NOT NULL DEFAULT '其他',
  focus_min INTEGER,
  note TEXT,
  active INTEGER NOT NULL DEFAULT 1,
  PRIMARY KEY(owner_id, id)
);

CREATE TABLE IF NOT EXISTS day_logs (
  owner_id INTEGER NOT NULL,
  day TEXT NOT NULL,
  tasks TEXT NOT NULL DEFAULT '[]',
  review TEXT NOT NULL DEFAULT '{}',
  focus_sec INTEGER NOT NULL DEFAULT 0,
  completion REAL NOT NULL DEFAULT 0,
  checked_in INTEGER NOT NULL DEFAULT 0,
  updated_at TEXT NOT NULL,
  PRIMARY KEY(owner_id, day)
);

CREATE TABLE IF NOT EXISTS audit_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  actor_id INTEGER NOT NULL,
  action TEXT NOT NULL,
  target_id INTEGER,
  detail TEXT,
  created_at TEXT NOT NULL
);
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def today_cn() -> str:
    return datetime.now(CN_TZ).date().isoformat()


def connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    # check_same_thread=False 是必须的：FastAPI 会把同步依赖和路由函数分派到
    # 线程池里的不同线程，同一个连接可能在两个线程间交接。连接本身是「每请求一个」，
    # 不会被两个请求同时持有，因此关闭该检查是安全的。
    conn = sqlite3.connect(DB_PATH, timeout=15, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=15000")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def get_db():
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    conn = connect()
    try:
        conn.executescript(SCHEMA)
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(plan_items)").fetchall()}
        if "focus_min" not in columns:
            conn.execute("ALTER TABLE plan_items ADD COLUMN focus_min INTEGER")
        conn.commit()
    finally:
        conn.close()


def row_to_dict(row) -> dict:
    return dict(row) if row is not None else None


_backup_state = {"day": None}


def backup_snapshot(force: bool = False) -> None:
    """每天落一份完整快照（含账号哈希），仅用于本地排障，不对外暴露。"""
    from .seed import TABLE_EXPORT

    day = today_cn()
    if not force and _backup_state["day"] == day:
        return
    try:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        conn = connect()
        try:
            payload = {"generatedAt": now_iso(), "tables": {}}
            for table in TABLE_EXPORT:
                rows = conn.execute(f"SELECT * FROM {table}").fetchall()
                payload["tables"][table] = [dict(r) for r in rows]
        finally:
            conn.close()
        target = BACKUP_DIR / f"study-{day}.json"
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
        _backup_state["day"] = day
    except Exception:
        pass
