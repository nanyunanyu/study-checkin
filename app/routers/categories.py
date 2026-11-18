import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from ..db import get_db, now_iso
from ..deps import current_account
from ..schemas import CategoryIn, CategoryNamesIn
from ..seed import SUBJECTS

router = APIRouter(prefix="/api/categories", tags=["categories"])
PRESET_NAMES = {name.casefold() for name in SUBJECTS}


def _clean_name(value: str) -> str:
    name = value.strip()
    if not name:
        raise HTTPException(status_code=400, detail="分类名称不能为空")
    if len(name) > 40:
        raise HTTPException(status_code=400, detail="分类名称不能超过 40 个字符")
    if name.casefold() in PRESET_NAMES:
        raise HTTPException(status_code=409, detail="该名称属于预设分类")
    return name


def _category(row) -> dict:
    return {"id": row["id"], "name": row["name"]}


@router.get("")
def list_categories(account=Depends(current_account), conn=Depends(get_db)):
    rows = conn.execute(
        "SELECT id, name FROM plan_categories WHERE owner_id=? ORDER BY id ASC",
        (account["id"],),
    ).fetchall()
    return {"presets": SUBJECTS, "custom": [_category(row) for row in rows]}


@router.post("", status_code=201)
def create_category(
    payload: CategoryIn, account=Depends(current_account), conn=Depends(get_db)
):
    name = _clean_name(payload.name)
    try:
        cursor = conn.execute(
            "INSERT INTO plan_categories(owner_id, name, created_at) VALUES (?,?,?)",
            (account["id"], name, now_iso()),
        )
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="该自定义分类已存在")
    conn.commit()
    row = conn.execute(
        "SELECT id, name FROM plan_categories WHERE id=? AND owner_id=?",
        (cursor.lastrowid, account["id"]),
    ).fetchone()
    return _category(row)


@router.post("/import")
def import_categories(
    payload: CategoryNamesIn,
    account=Depends(current_account),
    conn=Depends(get_db),
):
    from ..db import ensure_plan_categories

    ensure_plan_categories(conn, account["id"], payload.names)
    conn.commit()
    rows = conn.execute(
        "SELECT id, name FROM plan_categories WHERE owner_id=? ORDER BY id ASC",
        (account["id"],),
    ).fetchall()
    return {"presets": SUBJECTS, "custom": [_category(row) for row in rows]}


@router.patch("/{category_id}")
def rename_category(
    category_id: int,
    payload: CategoryIn,
    account=Depends(current_account),
    conn=Depends(get_db),
):
    owner_id = account["id"]
    row = conn.execute(
        "SELECT id, name FROM plan_categories WHERE id=? AND owner_id=?",
        (category_id, owner_id),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="分类不存在")
    name = _clean_name(payload.name)
    old_name = row["name"]
    try:
        conn.execute(
            "UPDATE plan_categories SET name=? WHERE id=? AND owner_id=?",
            (name, category_id, owner_id),
        )
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="该自定义分类已存在")

    # Current plan entries follow the rename; historical day snapshots keep their original labels.
    conn.execute(
        "UPDATE plan_items SET subject=? WHERE owner_id=? AND subject=? COLLATE NOCASE",
        (name, owner_id, old_name),
    )
    conn.commit()
    return {"id": category_id, "name": name}


@router.delete("/{category_id}")
def delete_category(
    category_id: int, account=Depends(current_account), conn=Depends(get_db)
):
    owner_id = account["id"]
    row = conn.execute(
        "SELECT id, name FROM plan_categories WHERE id=? AND owner_id=?",
        (category_id, owner_id),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="分类不存在")
    used = conn.execute(
        "SELECT 1 FROM plan_items WHERE owner_id=? AND subject=? COLLATE NOCASE LIMIT 1",
        (owner_id, row["name"]),
    ).fetchone()
    if used:
        raise HTTPException(status_code=409, detail="当前计划仍在使用该分类，请先更改计划分类")
    conn.execute(
        "DELETE FROM plan_categories WHERE id=? AND owner_id=?",
        (category_id, owner_id),
    )
    conn.commit()
    return {"ok": True}
