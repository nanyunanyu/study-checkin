import os
import re
import uuid

from .db import now_iso
from .security import hash_password

TABLE_EXPORT = ["accounts", "plan_items", "plan_categories", "plan_history", "day_logs"]

SUBJECTS = ["英语", "语文", "数学", "专业课", "网课", "练习", "背诵", "复盘", "休息", "其他"]

# 源文档《专升本每日学习打卡表》的 24 个时间段
DEFAULT_PLAN = [
    ("07:10", "07:40", "起床+早餐，听英语音频磨耳朵", "英语"),
    ("07:40", "08:25", "晨背（古诗文 / 英语单词，隔天轮换）", "背诵"),
    ("08:25", "08:35", "缓冲：整理资料、调试平板", "其他"),
    ("08:35", "09:40", "网课1（跟随学校课表）", "网课"),
    ("09:40", "09:50", "休息：喝水、远眺、活动手腕", "休息"),
    ("09:50", "10:55", "网课2（跟随学校课表）", "网课"),
    ("10:55", "11:05", "休息：简单整理课堂笔记", "休息"),
    ("11:05", "11:50", "网课3 / 空余刷题、预习", "网课"),
    ("11:50", "12:00", "收拾书包，离馆回寝室", "其他"),
    ("12:00", "14:00", "寝室：吃饭+午休（40–60分钟）", "休息"),
    ("14:00", "14:20", "路上+到馆就位，摆放资料", "其他"),
    ("14:20", "15:10", "配套练习（网课对应内容，PDF手写）", "练习"),
    ("15:10", "15:20", "短暂休息", "休息"),
    ("15:20", "16:10", "补齐另一科专项", "专业课"),
    ("16:10", "16:20", "间隙：整理错题", "复盘"),
    ("16:20", "17:10", "当日复盘：重点、错题、难背内容", "复盘"),
    ("17:10", "18:10", "晚饭+散步放松", "休息"),
    ("18:10", "19:00", "笔记补全、整理答题模板", "复盘"),
    ("19:00", "19:10", "休息", "休息"),
    ("19:10", "20:00", "滚动背诵（晨背+白天所学）", "背诵"),
    ("20:00", "20:10", "休息", "休息"),
    ("20:10", "20:50", "弹性任务：补习题 / 预习 / 攻克薄弱点", "练习"),
    ("20:50", "21:00", "收拾物品，核对今日任务", "其他"),
    ("21:00", "21:00", "离开图书馆回宿舍", "其他"),
]


def template_items():
    return [
        {
            "id": uuid.uuid4().hex,
            "sortOrder": index,
            "startTime": start,
            "endTime": end,
            "title": title,
            "subject": subject,
            "focusMin": None,
            "note": "",
            "active": True,
        }
        for index, (start, end, title, subject) in enumerate(DEFAULT_PLAN)
    ]


def copy_default_plan(conn, owner_id: int) -> None:
    rows = template_items()
    conn.executemany(
        "INSERT INTO plan_items(owner_id, id, sort_order, start_time, end_time, title, subject, note, active)"
        " VALUES (?,?,?,?,?,?,?,?,?)",
        [
            (
                owner_id,
                item["id"],
                item["sortOrder"],
                item["startTime"],
                item["endTime"],
                item["title"],
                item["subject"],
                item["note"],
                1,
            )
            for item in rows
        ],
    )


def create_account(conn, username, password, display_name=None, role="user", created_by=None):
    pwd_hash, salt, iterations = hash_password(password)
    cur = conn.execute(
        "INSERT INTO accounts(username, display_name, role, status, pwd_hash, pwd_salt, iterations, created_at, created_by)"
        " VALUES (?,?,?,'active',?,?,?,?,?)",
        (username, display_name, role, pwd_hash, salt, iterations, now_iso(), created_by),
    )
    owner_id = cur.lastrowid
    copy_default_plan(conn, owner_id)
    return owner_id


def ensure_seed(conn) -> None:
    has_superadmin = conn.execute(
        "SELECT 1 FROM accounts WHERE role='superadmin' LIMIT 1"
    ).fetchone()
    if not has_superadmin:
        username = os.environ.get("STUDY_ADMIN_USERNAME", "").strip()
        password = os.environ.get("STUDY_ADMIN_PASSWORD", "")
        if not re.fullmatch(r"[A-Za-z0-9_]{4,32}", username) or len(password) < 8:
            raise RuntimeError(
                "首次启动请设置 STUDY_ADMIN_USERNAME（4–32 位字母、数字或下划线）"
                "和 STUDY_ADMIN_PASSWORD（至少 8 位）"
            )

        if conn.execute("SELECT 1 FROM accounts WHERE username=?", (username,)).fetchone():
            raise RuntimeError("STUDY_ADMIN_USERNAME 已被使用，请为初始管理员设置一个新账号")

        create_account(conn, username, password, display_name="超级管理员", role="superadmin")

    for row in conn.execute("SELECT id FROM accounts").fetchall():
        has_plan = conn.execute(
            "SELECT 1 FROM plan_items WHERE owner_id=? LIMIT 1", (row["id"],)
        ).fetchone()
        if not has_plan:
            copy_default_plan(conn, row["id"])

    conn.commit()
