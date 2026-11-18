# 专升本每日学习打卡

照着 `专升本每日学习打卡表.docx` 做的在线打卡站：24 个时间段的作息表 + 番茄钟 + 每日打卡 + 热力图，带自己的账号体系，不开放注册。

## 技术栈

- 前端：Vue 3（`<script setup>`）+ Vite + Pinia，Element Plus + 自定义 CSS 主题适配
- 后端：FastAPI，单进程同时提供 API 与 SPA 静态资源
- 数据库：SQLite（WAL 模式），文件放在 `data/study.db`
- 鉴权：PBKDF2-HMAC-SHA256 + Bearer 会话令牌，令牌只存 SHA-256 摘要

前后端同源部署，一个端口跑完，不需要额外的数据库服务。

## 本地运行

```bash
# 1. 装后端依赖
pip install -r requirements.txt

# 2. 构建前端（产物直接输出到 app/webui）
cd frontend
npm install
npm run build
cd ..

# 3. 首次启动（在 Bash 或 Zsh 中运行）
read -r STUDY_ADMIN_USERNAME
read -rs STUDY_ADMIN_PASSWORD
STUDY_ADMIN_USERNAME="$STUDY_ADMIN_USERNAME" STUDY_ADMIN_PASSWORD="$STUDY_ADMIN_PASSWORD" python server.py
```

首次启动需要 4–32 位字母、数字或下划线组成的账号，以及至少 8 位的密码。第一行 `read` 等待输入账号，第二行等待输入密码（输入时不会显示字符）。应用会创建初始管理员并生成默认计划。数据库已有管理员时，直接运行 `python server.py` 即可。

打开 http://127.0.0.1:8000 登录。需要更换端口时，可设置 `PORT` 环境变量。

## 功能

- **今日**：24 条时间表逐项勾选，进度环 + 完成率 + 连续打卡 + 当日专注；「完成打卡」是独立动作，勾任务不会自动算打卡
- **计时器**：番茄钟 / 正计时 / 倒计时三种模式，可绑定到具体任务；中途点「结束本轮」也会把已专注的时长记到当天
- **计划**：通过页面内弹窗批量新增计划，可自定义类别、备注和专注时间，并支持展开详情与调整顺序；保存后从今天起生效，历史记录是按天快照，不受影响
- **统计**：一年热力图（完成率 / 专注时长两种口径）、近 30 天完成率、科目分布、连续打卡与累计专注
- **后台**（仅超管）：建号、停用、重置密码、删除；只读查看任意账号的学习数据；所有写操作记审计日志
- **外观**：在配色选择器中即时预览淡绿渐变 / 淡蓝渐变 / 乳白 / 纯白 / 夜间 / 跟随系统，选择保存在本机
- **分类**：计划类别通过预设 / 自定义分组选择；自定义分类仅当前账号可见，可新增、重命名和删除。重命名同步当前计划，历史记录保留原名称；使用中的分类须先从计划中移除并保存才能删除。首次升级自动收集计划及历史记录中的旧分类，导入备份时合并分类。

## 账号与权限

- 不开放注册，账号只能由超级管理员在后台创建；新账号会自动复制一份 24 条默认计划
- 超管可以要求新账号「首次登录修改密码」，登录后强制弹出改密，改完才能用
- 登录连续失败 5 次锁定 10 分钟，登录失败会提示还剩几次机会
- 会话 30 天滑动过期；改密码会踢掉其它设备，只保留当前这台
- 数据按账号隔离：`plan_items` 和 `day_logs` 都以 `owner_id` 为复合主键的一部分，所有查询强制带 owner 过滤
- 超管不能停用、删除或降级自己，系统至少保留一个超级管理员

## 目录

```
study-checkin/
├── app/                 FastAPI 后端
│   ├── main.py          应用入口 + SPA 兜底路由
│   ├── db.py            建库、连接、每日快照
│   ├── security.py      口令哈希、令牌
│   ├── seed.py          种子账号与 24 条默认计划
│   ├── deps.py          鉴权依赖（current_account / require_superadmin）
│   ├── routers/         auth / data / admin
│   └── webui/           前端构建产物（由 vite 输出）
├── frontend/            Vue 3 前端源码
└── data/                SQLite 数据库与每日快照（不进版本库）
```

## 数据备份

`data/backups/study-YYYY-MM-DD.json` 每天落一份全量快照（含账号哈希），仅用于本地排障，不对外暴露接口。要迁移或备份，直接备份整个 `data/` 目录即可。

## 开发验证

```bash
python3 -m pip install -r requirements-dev.txt
python3 -m pytest -q
cd frontend
npm run build
```

分类接口测试使用独立的临时数据库，覆盖账号隔离、历史分类迁移、重命名、删除保护与导入导出。
