from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse

from .db import connect, get_db, init_db
from .routers import admin, auth, categories, data
from .seed import ensure_seed

WEBUI_DIR = Path(__file__).resolve().parent / "webui"

app = FastAPI(title="专升本每日学习打卡", docs_url=None, redoc_url=None, openapi_url=None)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    conn = connect()
    try:
        ensure_seed(conn)
    finally:
        conn.close()


@app.get("/api/health")
def health(conn=Depends(get_db)):
    # 顺手碰一下数据库，确认连接正常；不暴露任何业务数据
    conn.execute("SELECT 1").fetchone()
    return {"ok": True}


app.include_router(auth.router)
app.include_router(data.router)
app.include_router(categories.router)
app.include_router(admin.router)


@app.get("/{full_path:path}")
def serve_spa(full_path: str):
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="接口不存在")

    index = WEBUI_DIR / "index.html"
    if not index.exists():
        return {
            "message": "前端尚未构建，请在 frontend 目录执行 npm install && npm run build",
        }

    candidate = (WEBUI_DIR / full_path).resolve()
    try:
        inside = candidate.is_relative_to(WEBUI_DIR.resolve())
    except AttributeError:
        inside = str(candidate).startswith(str(WEBUI_DIR.resolve()))
    if full_path and inside and candidate.is_file():
        return FileResponse(candidate)
    return FileResponse(index)
