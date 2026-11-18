import json

from .db import now_iso
from .serialize import plan_row_to_item


def load_plan(conn, owner_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM plan_items WHERE owner_id=? ORDER BY sort_order ASC", (owner_id,)
    ).fetchall()
    return [plan_row_to_item(row) for row in rows]


def archive_plan(conn, owner_id: int, items: list[dict]) -> None:
    conn.execute(
        "INSERT INTO plan_history(owner_id, replaced_at, item_count, items) VALUES (?,?,?,?)",
        (owner_id, now_iso(), len(items), json.dumps(items, ensure_ascii=False)),
    )
