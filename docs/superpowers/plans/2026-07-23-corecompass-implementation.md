# CoreCompass 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 8 天内交付 CoreCompass —— 校园项目"伪需求"粉碎机，一个具备硬验收、动态重算、主动打扰三大突出点的项目拆解 Agent。

**架构：** FastAPI 后端 + Alpine.js 前端 + SQLite + APScheduler + 豆包 LLM。后端按服务分层（state_machine / llm / services / routes），前端单页多面板。

**技术栈：** Python 3.11+、FastAPI、sqlite3（原生）、APScheduler、volcengine-python-sdk（豆包）、sqlparse、jsonrepair、pyyaml、httpx、pytest、pytest-asyncio、freezegun、Alpine.js 3.x

**对应规格：** `docs/superpowers/specs/2026-07-23-corecompass-design.md`

**进度跟踪约定：** 每个任务头部【用户视角】= 该任务完成后你能看到什么效果，便于非技术用户跟踪。

---

## 文件结构

```
CoreCompass/
├── backend/
│   ├── app/
│   │   ├── main.py                # FastAPI 入口、路由注册、CORS、启动调度器
│   │   ├── config.py              # 配置加载
│   │   ├── db.py                  # SQLite 连接与初始化
│   │   ├── schema.sql             # 建表 SQL（6 张表）
│   │   ├── models.py              # 数据访问层
│   │   ├── state_machine.py       # 状态机（确定性）
│   │   ├── llm/{client.py, prompts.py}
│   │   ├── services/{project,validate,replan,notify}_service.py
│   │   └── routes/{projects,tasks,validate,replan,notify}.py
│   ├── tests/
│   └── requirements.txt, .env.example
├── frontend/
│   ├── index.html
│   └── static/{app.js, style.css, components/}
├── data/                          # 运行时生成 corecompass.db
├── docs/superpowers/{specs,plans}/
├── README.md, .gitignore
└── 参赛材料/                      # D8 交付物
```

**职责边界：**
- `state_machine.py`：纯函数，不碰 LLM/DB，所有状态推进的唯一入口
- `services/*`：编排 LLM + models + state_machine，业务逻辑层
- `routes/*`：仅 HTTP 适配，无业务逻辑
- `llm/client.py`：屏蔽 SDK 细节，所有 LLM 调用经此

---

## 任务 0：环境与脚手架

【用户视角】`uvicorn app.main:app` 能启动，浏览器看到首页标题，`/health` 返回 ok。

**文件：** 创建 `.gitignore`、`backend/requirements.txt`、`backend/.env.example`、`backend/app/{main,config,db}.py`、`backend/app/schema.sql`、`frontend/index.html`、`frontend/static/{app.js,style.css}`、`README.md`

- [ ] **步骤 1：.gitignore**

```
__pycache__/
*.pyc
.venv/
.env
data/*.db
node_modules/
.DS_Store
.vscode/
.idea/
*.log
```

- [ ] **步骤 2：requirements.txt**

```
fastapi==0.115.0
uvicorn[standard]==0.30.6
volcengine-python-sdk==1.0.115
sqlparse==0.5.1
jsonrepair==0.30.0
pyyaml==6.0.2
apscheduler==3.10.4
python-multipart==0.0.9
httpx==0.27.2
python-dotenv==1.0.1
pytest==8.3.3
pytest-asyncio==0.24.0
freezegun==1.5.1
```

- [ ] **步骤 3：.env.example**

```
VOLC_AK=your_access_key
VOLC_SK=your_secret_key
VOLC_MODEL=doubao-pro-32k
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxx
FEISHU_SECRET=your_signing_secret_optional
SCHEDULER_INTERVAL_MINUTES=1440
```

- [ ] **步骤 4：schema.sql（6 张表）**

```sql
CREATE TABLE IF NOT EXISTS projects (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL, deadline TEXT NOT NULL,
  team_size INTEGER NOT NULL, topic_desc TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',
  created_at TEXT NOT NULL DEFAULT (datetime('now')));
CREATE TABLE IF NOT EXISTS milestones (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  name TEXT NOT NULL, order_idx INTEGER NOT NULL,
  status TEXT NOT NULL DEFAULT 'planned',
  expected_artifact_type TEXT NOT NULL,
  UNIQUE(project_id, order_idx));
CREATE TABLE IF NOT EXISTS tasks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  milestone_id INTEGER NOT NULL REFERENCES milestones(id) ON DELETE CASCADE,
  project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  title TEXT NOT NULL, description TEXT,
  priority TEXT NOT NULL DEFAULT 'optional',
  difficulty TEXT NOT NULL DEFAULT 'mid',
  est_effort_days REAL NOT NULL DEFAULT 1.0,
  status TEXT NOT NULL DEFAULT 'planned',
  start_date TEXT, due_date TEXT, completed_at TEXT);
CREATE TABLE IF NOT EXISTS checkins (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  note TEXT, created_at TEXT NOT NULL DEFAULT (datetime('now')));
CREATE TABLE IF NOT EXISTS validation_records (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  milestone_id INTEGER NOT NULL REFERENCES milestones(id) ON DELETE CASCADE,
  filename TEXT NOT NULL, file_type TEXT NOT NULL,
  result TEXT NOT NULL, fail_reasons TEXT,
  llm_used INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT (datetime('now')));
CREATE TABLE IF NOT EXISTS replan_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  gap_days REAL NOT NULL, proposal TEXT,
  applied INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT (datetime('now')));
CREATE TABLE IF NOT EXISTS notifications (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
  type TEXT NOT NULL, content TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'sent',
  response TEXT, created_at TEXT NOT NULL DEFAULT (datetime('now')));
```

- [ ] **步骤 5：config.py**

```python
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "corecompass.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
VOLC_AK = os.getenv("VOLC_AK", "")
VOLC_SK = os.getenv("VOLC_SK", "")
VOLC_MODEL = os.getenv("VOLC_MODEL", "doubao-pro-32k")
FEISHU_WEBHOOK_URL = os.getenv("FEISHU_WEBHOOK_URL", "")
FEISHU_SECRET = os.getenv("FEISHU_SECRET", "")
SCHEDULER_INTERVAL_MINUTES = int(os.getenv("SCHEDULER_INTERVAL_MINUTES", "1440"))
```

- [ ] **步骤 6：db.py**

```python
import sqlite3
from pathlib import Path
from app import config

def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    schema_path = Path(__file__).parent / "schema.sql"
    with get_conn() as conn:
        conn.executescript(schema_path.read_text(encoding="utf-8"))
```

- [ ] **步骤 7：main.py（仅 /health + 静态前端）**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from app.db import init_db

app = FastAPI(title="CoreCompass")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
def startup():
    init_db()

@app.get("/health")
def health():
    return {"status": "ok"}

frontend_dir = Path(__file__).resolve().parent.parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=frontend_dir / "static"), name="static")
    @app.get("/")
    def index():
        return FileResponse(frontend_dir / "index.html")
```

- [ ] **步骤 8：前端骨架**

`frontend/index.html`:
```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <title>CoreCompass · 校园项目粉碎机</title>
  <link rel="stylesheet" href="/static/style.css">
  <script defer src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js"></script>
</head>
<body>
  <header><h1>CoreCompass</h1><p>校园项目"伪需求"粉碎机</p></header>
  <main x-data="app()"><p>脚手架就绪，等待功能面板。</p></main>
  <script src="/static/app.js"></script>
</body>
</html>
```

`frontend/static/app.js`:
```javascript
function app() { return { message: 'hello' } }
```

`frontend/static/style.css`:
```css
* { box-sizing: border-box; }
body { font-family: -apple-system, "Microsoft YaHei", sans-serif; margin: 0; background: #f5f7fa; color: #333; }
header { background: #1a2b4a; color: white; padding: 16px 32px; }
header h1 { margin: 0; }
header p { margin: 4px 0 0; opacity: 0.7; }
main { padding: 24px 32px; max-width: 1200px; margin: 0 auto; }
```

- [ ] **步骤 9：README.md**

```markdown
# CoreCompass
校园项目"伪需求"粉碎机。

## 启动
1. 复制 `backend/.env.example` 为 `backend/.env`，填火山引擎凭证和飞书 webhook
2. `pip install -r backend/requirements.txt`
3. `cd backend && uvicorn app.main:app --reload`
4. 浏览器打开 http://localhost:8000

## 测试
`cd backend && pytest -v`
```

- [ ] **步骤 10：验证启动**

运行 `cd backend && pip install -r requirements.txt && python -c "from app.main import app; print('ok')"`，预期输出 `ok`。
启动 `uvicorn app.main:app --reload`，`/health` 返回 `{"status":"ok"}`，`/` 看到首页。

- [ ] **步骤 11：Commit**

```bash
git add .
git commit -m "feat: 项目脚手架（FastAPI + SQLite + Alpine.js 骨架）"
```

---

## 任务 1：数据模型与状态机

【用户视角】后端能创建/查询项目和任务，能模拟"任务完成/逾期/被砍"状态变化。无 UI，单元测试验证。

**文件：** 创建 `backend/app/{models,state_machine}.py`、`backend/tests/{conftest,test_state_machine}.py`

- [ ] **步骤 1：test_state_machine.py（先红）**

```python
import pytest
from app.state_machine import (
    transition_task, transition_milestone, transition_project,
    TaskStatus, MilestoneStatus, ProjectStatus, InvalidTransition)

def test_task_planned_to_doing():
    assert transition_task(TaskStatus.PLANNED, "start") == TaskStatus.DOING
def test_task_doing_to_done():
    assert transition_task(TaskStatus.DOING, "complete") == TaskStatus.DONE
def test_task_doing_to_overdue():
    assert transition_task(TaskStatus.DOING, "overdue") == TaskStatus.OVERDUE
def test_task_any_to_cut():
    for s in [TaskStatus.PLANNED, TaskStatus.DOING, TaskStatus.OVERDUE]:
        assert transition_task(s, "cut") == TaskStatus.CUT
def test_invalid_transition_raises():
    with pytest.raises(InvalidTransition):
        transition_task(TaskStatus.DONE, "start")
def test_milestone_lock():
    assert transition_milestone(MilestoneStatus.IN_PROGRESS, "lock") == MilestoneStatus.LOCKED
def test_project_crisis_and_back():
    assert transition_project(ProjectStatus.ACTIVE, "crisis") == ProjectStatus.CRISIS
    assert transition_project(ProjectStatus.CRISIS, "resolve") == ProjectStatus.ACTIVE
```

- [ ] **步骤 2：运行验证失败**

`pytest tests/test_state_machine.py -v` → FAIL，模块不存在。

- [ ] **步骤 3：state_machine.py**

```python
from enum import Enum

class TaskStatus(str, Enum):
    PLANNED = "planned"; DOING = "doing"; DONE = "done"; OVERDUE = "overdue"; CUT = "cut"
class MilestoneStatus(str, Enum):
    PLANNED = "planned"; IN_PROGRESS = "in_progress"; LOCKED = "locked"; DONE = "done"
class ProjectStatus(str, Enum):
    ACTIVE = "active"; CRISIS = "crisis"; COMPLETED = "completed"

class InvalidTransition(Exception):
    pass

_TASK = {
    TaskStatus.PLANNED: {"start": TaskStatus.DOING, "cut": TaskStatus.CUT},
    TaskStatus.DOING: {"complete": TaskStatus.DONE, "overdue": TaskStatus.OVERDUE, "cut": TaskStatus.CUT},
    TaskStatus.OVERDUE: {"complete": TaskStatus.DONE, "cut": TaskStatus.CUT},
    TaskStatus.DONE: {}, TaskStatus.CUT: {},
}
_MILESTONE = {
    MilestoneStatus.PLANNED: {"start": MilestoneStatus.IN_PROGRESS},
    MilestoneStatus.IN_PROGRESS: {"lock": MilestoneStatus.LOCKED, "complete": MilestoneStatus.DONE},
    MilestoneStatus.LOCKED: {"unlock": MilestoneStatus.IN_PROGRESS, "complete": MilestoneStatus.DONE},
    MilestoneStatus.DONE: {},
}
_PROJECT = {
    ProjectStatus.ACTIVE: {"crisis": ProjectStatus.CRISIS, "complete": ProjectStatus.COMPLETED},
    ProjectStatus.CRISIS: {"resolve": ProjectStatus.ACTIVE, "complete": ProjectStatus.COMPLETED},
    ProjectStatus.COMPLETED: {},
}

def transition_task(current, event):
    allowed = _TASK.get(current, {})
    if event not in allowed:
        raise InvalidTransition(f"任务 {current.value} 不允许事件 {event}")
    return allowed[event]

def transition_milestone(current, event):
    allowed = _MILESTONE.get(current, {})
    if event not in allowed:
        raise InvalidTransition(f"里程碑 {current.value} 不允许事件 {event}")
    return allowed[event]

def transition_project(current, event):
    allowed = _PROJECT.get(current, {})
    if event not in allowed:
        raise InvalidTransition(f"项目 {current.value} 不允许事件 {event}")
    return allowed[event]
```

- [ ] **步骤 4：运行测试通过**

`pytest tests/test_state_machine.py -v` → 7 PASS。

- [ ] **步骤 5：models.py（CRUD 数据访问层）**

```python
from app.db import get_conn

def create_project(name, deadline, team_size, topic_desc):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO projects(name, deadline, team_size, topic_desc) VALUES(?,?,?,?)",
            (name, deadline, team_size, topic_desc))
        return cur.lastrowid

def get_project(pid):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()
        return dict(row) if row else None

def list_projects():
    with get_conn() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM projects ORDER BY id DESC").fetchall()]

def create_milestone(project_id, name, order_idx, expected_artifact_type):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO milestones(project_id, name, order_idx, expected_artifact_type) VALUES(?,?,?,?)",
            (project_id, name, order_idx, expected_artifact_type))
        return cur.lastrowid

def create_task(milestone_id, project_id, title, description, priority, difficulty,
                est_effort_days, start_date, due_date):
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO tasks(milestone_id, project_id, title, description, priority,
               difficulty, est_effort_days, start_date, due_date) VALUES(?,?,?,?,?,?,?,?,?)""",
            (milestone_id, project_id, title, description, priority, difficulty,
             est_effort_days, start_date, due_date))
        return cur.lastrowid

def get_task(task_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        return dict(row) if row else None

def get_milestone(mid):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM milestones WHERE id=?", (mid,)).fetchone()
        return dict(row) if row else None

def list_milestones(pid):
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM milestones WHERE project_id=? ORDER BY order_idx", (pid,)).fetchall()]

def list_tasks_by_project(pid, include_cut=False):
    sql = "SELECT * FROM tasks WHERE project_id=?"
    if not include_cut:
        sql += " AND status != 'cut'"
    sql += " ORDER BY due_date"
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(sql, (pid,)).fetchall()]

def update_task_status(task_id, status, completed_at=None):
    with get_conn() as conn:
        conn.execute("UPDATE tasks SET status=?, completed_at=? WHERE id=?",
                     (status, completed_at, task_id))

def update_task(task_id, **fields):
    allowed = {"priority", "difficulty", "est_effort_days", "status", "due_date", "start_date"}
    sets, vals = [], []
    for k, v in fields.items():
        if k in allowed:
            sets.append(f"{k}=?"); vals.append(v)
    if not sets:
        return
    vals.append(task_id)
    with get_conn() as conn:
        conn.execute(f"UPDATE tasks SET {','.join(sets)} WHERE id=?", vals)

def update_milestone_status(mid, status):
    with get_conn() as conn:
        conn.execute("UPDATE milestones SET status=? WHERE id=?", (status, mid))

def update_project_status(pid, status):
    with get_conn() as conn:
        conn.execute("UPDATE projects SET status=? WHERE id=?", (status, pid))

def insert_checkin(task_id, note):
    with get_conn() as conn:
        conn.execute("INSERT INTO checkins(task_id, note) VALUES(?,?)", (task_id, note))

def insert_validation(mid, filename, file_type, result, fail_reasons, llm_used):
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO validation_records(milestone_id, filename, file_type, result,
               fail_reasons, llm_used) VALUES(?,?,?,?,?,?)""",
            (mid, filename, file_type, result, fail_reasons, llm_used))
        return cur.lastrowid

def insert_replan_log(pid, gap_days, proposal, applied):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO replan_logs(project_id, gap_days, proposal, applied) VALUES(?,?,?,?)",
            (pid, gap_days, proposal, applied))
        return cur.lastrowid

def insert_notification(pid, type, content, status, response):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO notifications(project_id, type, content, status, response) VALUES(?,?,?,?,?)",
            (pid, type, content, status, response))
        return cur.lastrowid

def list_notifications(pid=None, limit=50):
    with get_conn() as conn:
        if pid:
            rows = conn.execute(
                "SELECT * FROM notifications WHERE project_id=? ORDER BY id DESC LIMIT ?",
                (pid, limit)).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM notifications ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

def list_overdue_tasks(pid=None):
    sql = "SELECT * FROM tasks WHERE status='overdue'"
    params = ()
    if pid:
        sql += " AND project_id=?"; params = (pid,)
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
```

- [ ] **步骤 6：conftest.py（内存 DB 夹具）**

```python
import sqlite3
from pathlib import Path
import pytest

@pytest.fixture(autouse=True)
def in_memory_db(monkeypatch):
    conn = sqlite3.connect(":memory:", detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    schema = Path(__file__).resolve().parent.parent / "app" / "schema.sql"
    conn.executescript(schema.read_text(encoding="utf-8"))
    import app.db as db
    monkeypatch.setattr(db, "get_conn", lambda: conn)
    yield conn
```

- [ ] **步骤 7：运行全部测试**

`pytest -v` → 7 PASS。

- [ ] **步骤 8：Commit**

```bash
git add backend/app/models.py backend/app/state_machine.py backend/tests/
git commit -m "feat: 数据模型与状态机（含 7 个状态机测试）"
```

---

## 任务 2：LLM 客户端封装

【用户视角】后端统一函数调豆包生成 JSON，失败时自动重试 + JSON 修复 + fallback 模板，永不抛异常崩主流程。

**文件：** 创建 `backend/app/llm/__init__.py`、`backend/app/llm/{client,prompts}.py`、`backend/tests/test_llm_client.py`

- [ ] **步骤 1：prompts.py（三类模板 + 两个 fallback）**

```python
INITIAL_PLAN_PROMPT = """你是项目拆解专家。根据课题生成里程碑和周任务。
课题：{topic}
团队人数：{team_size}
截止日期：{deadline}

输出严格 JSON（不要 markdown 代码块）：
{{
  "milestones": [
    {{"name": "...", "expected_artifact_type": "sql|md|code|json|other", "tasks": [
      {{"title": "...", "description": "...", "priority": "core|optional",
        "difficulty": "high|mid|low", "est_effort_days": 1.5, "week": 1}}
    ]}}
  ]
}}
要求：4-6 个里程碑，按 SDLC 顺序；每里程碑 2-4 任务；core/optional 比例约 6:4。
"""

REPLAN_PROMPT = """项目出现进度缺口，需要砍/降级任务。
剩余天数：{remaining_days}
团队人数：{team_size}
缺口（人天）：{gap_days}
当前未完成任务：
{tasks_json}

输出严格 JSON：
{{
  "cut_tasks": [任务id],
  "downgrade_tasks": [{{"id": 任务id, "from": "原难度", "to": "降级后难度", "new_effort": 0.5}}],
  "rationale": "简短说明"
}}
铁律：只能砍 priority=optional 的任务；core 任务只能降级不能砍；降级后 est_effort 必须减少。
"""

VALIDATE_FALLBACK_PROMPT = """校验以下文件是否符合里程碑要求。
里程碑名：{milestone_name}
文件类型：{file_type}
文件内容（截断）：
---
{content}
---
输出严格 JSON：{{"pass": true/false, "reasons": ["原因1"]}}
"""

FALLBACK_INITIAL_PLAN = {
    "milestones": [
        {"name": "需求分析", "expected_artifact_type": "md", "tasks": [
            {"title": "需求文档", "description": "撰写需求规格说明", "priority": "core",
             "difficulty": "mid", "est_effort_days": 1.0, "week": 1}]},
        {"name": "数据库设计", "expected_artifact_type": "sql", "tasks": [
            {"title": "ER 图与表结构", "description": "设计核心表", "priority": "core",
             "difficulty": "mid", "est_effort_days": 1.0, "week": 2}]},
        {"name": "核心实现", "expected_artifact_type": "code", "tasks": [
            {"title": "后端 API", "description": "实现核心接口", "priority": "core",
             "difficulty": "high", "est_effort_days": 2.0, "week": 3},
            {"title": "前端页面", "description": "实现主要界面", "priority": "optional",
             "difficulty": "mid", "est_effort_days": 1.5, "week": 3}]},
        {"name": "测试与部署", "expected_artifact_type": "md", "tasks": [
            {"title": "测试报告", "description": "功能测试与缺陷修复", "priority": "optional",
             "difficulty": "mid", "est_effort_days": 1.0, "week": 4}]}]
}

FALLBACK_REPLAN_PROPOSAL = {
    "cut_tasks": [], "downgrade_tasks": [],
    "rationale": "AI 提案失败，建议手动降级可选任务"
}
```

- [ ] **步骤 2：client.py（豆包封装 + 重试 + JSON 修复 + fallback）**

```python
import json
import re
import time
import logging
from typing import Optional
from volcenginesdkarkruntime import Ark
from jsonrepair import repair_json
from app import config
from app.llm.prompts import (INITIAL_PLAN_PROMPT, REPLAN_PROMPT, VALIDATE_FALLBACK_PROMPT,
                              FALLBACK_INITIAL_PLAN, FALLBACK_REPLAN_PROPOSAL)

logger = logging.getLogger(__name__)
_client: Optional[Ark] = None

class LLMUnavailableError(Exception):
    pass

def get_client() -> Ark:
    global _client
    if _client is None:
        _client = Ark(ak=config.VOLC_AK, sk=config.VOLC_SK)
    return _client

def parse_json_robust(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    try:
        return json.loads(repair_json(text))
    except Exception:
        pass
    m = re.search(r"```(?:json)?\s*(.+?)```", text, re.DOTALL)
    if m:
        try:
            return json.loads(repair_json(m.group(1)))
        except Exception:
            pass
    raise json.JSONDecodeError("无法解析为 JSON", text, 0)

def call_llm(prompt: str, max_retries: int = 1) -> dict:
    last_err = None
    for attempt in range(max_retries + 1):
        try:
            resp = get_client().chat.completions.create(
                model=config.VOLC_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3)
            return parse_json_robust(resp.choices[0].message.content)
        except Exception as e:
            logger.warning(f"LLM 调用失败 attempt={attempt}: {e}")
            last_err = e
            if attempt < max_retries:
                time.sleep(2)
    raise LLMUnavailableError(str(last_err))

def generate_initial_plan(topic, team_size, deadline):
    try:
        return call_llm(INITIAL_PLAN_PROMPT.format(
            topic=topic, team_size=team_size, deadline=deadline))
    except LLMUnavailableError:
        logger.error("初始计划 LLM 失败，用 fallback 模板")
        return FALLBACK_INITIAL_PLAN

def generate_replan_proposal(remaining_days, team_size, gap_days, tasks_json):
    try:
        return call_llm(REPLAN_PROMPT.format(
            remaining_days=remaining_days, team_size=team_size,
            gap_days=gap_days, tasks_json=tasks_json))
    except LLMUnavailableError:
        logger.error("重规划 LLM 失败，用 fallback")
        return FALLBACK_REPLAN_PROPOSAL

def validate_with_llm(milestone_name, file_type, content):
    try:
        return call_llm(VALIDATE_FALLBACK_PROMPT.format(
            milestone_name=milestone_name, file_type=file_type, content=content[:8000]))
    except LLMUnavailableError:
        return {"pass": False, "reasons": ["AI 校验失败，请人工确认"]}
```

- [ ] **步骤 3：__init__.py**

```python
from app.llm import client
```

- [ ] **步骤 4：test_llm_client.py（mock 豆包）**

```python
import pytest
from unittest.mock import patch, MagicMock
from app.llm import client
from app.llm.client import parse_json_robust, LLMUnavailableError

def test_parse_json_robust_plain():
    assert parse_json_robust('{"a": 1}') == {"a": 1}
def test_parse_json_robust_with_codeblock():
    assert parse_json_robust('```json\n{"a": 2}\n```') == {"a": 2}
def test_parse_json_robust_with_trailing_comma():
    assert parse_json_robust('{"a": 1,}') == {"a": 1}
def test_call_llm_success():
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content='{"ok": true}'))]
    with patch.object(client, "get_client", return_value=MagicMock(
        chat=MagicMock(completions=MagicMock(create=MagicMock(return_value=mock_resp))))):
        assert client.call_llm("test") == {"ok": True}
def test_call_llm_retry_then_fail():
    with patch.object(client, "get_client", return_value=MagicMock(
        chat=MagicMock(completions=MagicMock(create=MagicMock(side_effect=Exception("net")))))):
        with pytest.raises(LLMUnavailableError):
            client.call_llm("test", max_retries=1)
def test_generate_initial_plan_fallback():
    with patch.object(client, "call_llm", side_effect=LLMUnavailableError("down")):
        result = client.generate_initial_plan("topic", 3, "2026-08-01")
        assert "milestones" in result and len(result["milestones"]) >= 3
```

- [ ] **步骤 5：运行测试**

`pytest tests/test_llm_client.py -v` → 6 PASS。

- [ ] **步骤 6：Commit**

```bash
git add backend/app/llm/ backend/tests/test_llm_client.py
git commit -m "feat: LLM 客户端封装（豆包 + 重试 + JSON 修复 + fallback 模板）"
```

---

## 任务 3：项目创建 + 初始计划生成

【用户视角】POST /api/projects 接收课题 → 调 LLM 生成里程碑+任务 → 写入 DB → 返回完整项目结构。

**文件：** 创建 `backend/app/services/__init__.py`、`backend/app/services/project_service.py`、`backend/app/routes/__init__.py`、`backend/app/routes/projects.py`、`backend/tests/test_project_service.py`
修改：`backend/app/main.py`

- [ ] **步骤 1：project_service.py**

```python
from datetime import datetime, timedelta
from app import models
from app.llm import client

def create_project_with_plan(name, deadline, team_size, topic_desc):
    pid = models.create_project(name, deadline, team_size, topic_desc)
    plan = client.generate_initial_plan(topic_desc, team_size, deadline)
    for idx, ms in enumerate(plan.get("milestones", [])):
        mid = models.create_milestone(
            pid, ms["name"], idx, ms.get("expected_artifact_type", "other"))
        for t in ms.get("tasks", []):
            week = t.get("week", idx + 1)
            t_start = datetime.now() + timedelta(weeks=week - 1)
            t_due = t_start + timedelta(days=7)
            models.create_task(
                milestone_id=mid, project_id=pid,
                title=t["title"], description=t.get("description", ""),
                priority=t.get("priority", "optional"),
                difficulty=t.get("difficulty", "mid"),
                est_effort_days=t.get("est_effort_days", 1.0),
                start_date=t_start.isoformat(),
                due_date=t_due.isoformat())
    return pid

def get_project_detail(pid):
    return {
        "project": models.get_project(pid),
        "milestones": models.list_milestones(pid),
        "tasks": models.list_tasks_by_project(pid)}
```

- [ ] **步骤 2：services/__init__.py**

```python
from app.services import project_service
```

- [ ] **步骤 3：routes/projects.py**

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services import project_service
from app import models

router = APIRouter()

class ProjectCreate(BaseModel):
    name: str
    deadline: str
    team_size: int
    topic_desc: str

@router.post("/api/projects")
def create_project(req: ProjectCreate):
    try:
        pid = project_service.create_project_with_plan(
            req.name, req.deadline, req.team_size, req.topic_desc)
        return {"project_id": pid, "detail": project_service.get_project_detail(pid)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/projects")
def list_projects():
    return models.list_projects()

@router.get("/api/projects/{pid}")
def get_project(pid: int):
    return project_service.get_project_detail(pid)
```

- [ ] **步骤 4：routes/__init__.py**

```python
from app.routes import projects
```

- [ ] **步骤 5：修改 main.py 注册路由**

在 main.py `init_db()` 后添加：
```python
from app.routes import projects
app.include_router(projects.router)
```

- [ ] **步骤 6：test_project_service.py**

```python
import pytest
from unittest.mock import patch
from app.services import project_service

FALLBACK_PLAN = {
    "milestones": [
        {"name": "需求", "expected_artifact_type": "md", "tasks": [
            {"title": "需求文档", "priority": "core", "est_effort_days": 1.0, "week": 1}]},
        {"name": "数据库", "expected_artifact_type": "sql", "tasks": [
            {"title": "表结构", "priority": "core", "est_effort_days": 1.0, "week": 2}]}]}

@patch("app.services.project_service.client.generate_initial_plan", return_value=FALLBACK_PLAN)
def test_create_project_with_plan(mock_llm):
    pid = project_service.create_project_with_plan(
        "二手平台", "2026-08-20", 3, "校园二手交易平台")
    detail = project_service.get_project_detail(pid)
    assert detail["project"]["name"] == "二手平台"
    assert len(detail["milestones"]) == 2
    assert len(detail["tasks"]) == 2
    assert detail["tasks"][0]["priority"] == "core"
```

- [ ] **步骤 7：运行测试 + 手动验证 API**

`pytest tests/test_project_service.py -v` → 1 PASS。
启动后端，curl：
```
curl -X POST http://localhost:8000/api/projects -H "Content-Type: application/json" -d "{\"name\":\"二手平台\",\"deadline\":\"2026-08-20\",\"team_size\":3,\"topic_desc\":\"校园二手交易平台\"}"
```
预期返回含 project_id、milestones、tasks 的 JSON。

- [ ] **步骤 8：Commit**

```bash
git add backend/app/services/ backend/app/routes/ backend/app/main.py backend/tests/test_project_service.py
git commit -m "feat: 项目创建 + LLM 初始计划生成 API"
```

---

## 任务 4：实体验证后端（突出点①）

【用户视角】上传 .sql/.md/.py/.json 文件到里程碑关卡 → 系统校验 → 空文件被打回（locked）→ 合规文件通过解锁。

**文件：** 创建 `backend/app/services/validate_service.py`、`backend/app/routes/validate.py`、`backend/tests/{test_validate_sql,test_lock_milestone}.py`
修改：`backend/app/main.py`、`backend/app/routes/__init__.py`

- [ ] **步骤 1：test_validate_sql.py（先红）**

```python
from app.services import validate_service

VALID_SQL = """
CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT);
CREATE TABLE orders (id INTEGER PRIMARY KEY, user_id INTEGER, FOREIGN KEY (user_id) REFERENCES users(id));
"""
EMPTY_SQL = "-- nothing here"
NO_FK_SQL = """
CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT);
CREATE TABLE logs (id INTEGER PRIMARY KEY, msg TEXT);
"""

def test_valid_sql_passes():
    r = validate_service.validate_sql(VALID_SQL)
    assert r["pass"] is True and not r["reasons"]

def test_empty_sql_fails():
    r = validate_service.validate_sql(EMPTY_SQL)
    assert r["pass"] is False
    assert any("表" in x for x in r["reasons"])

def test_no_fk_fails():
    r = validate_service.validate_sql(NO_FK_SQL)
    assert r["pass"] is False
    assert any("外键" in x for x in r["reasons"])
```

- [ ] **步骤 2：运行验证失败**

`pytest tests/test_validate_sql.py -v` → FAIL，模块不存在。

- [ ] **步骤 3：validate_service.py**

```python
import re
import ast
import json
import yaml
import sqlparse
from typing import Dict, Any
from app import models
from app.llm import client
from app.state_machine import MilestoneStatus

def validate_sql(content: str) -> Dict[str, Any]:
    reasons = []
    sql_text = " ".join(str(p) for p in sqlparse.parse(content)).upper()
    if len(re.findall(r"CREATE\s+TABLE", sql_text)) < 2:
        reasons.append("表数量不足：< 2")
    if "PRIMARY KEY" not in sql_text:
        reasons.append("缺少 PRIMARY KEY")
    if "FOREIGN KEY" not in sql_text:
        reasons.append("缺少 FOREIGN KEY（外键）")
    return {"pass": not reasons, "reasons": reasons}

def validate_md(content: str) -> Dict[str, Any]:
    reasons = []
    if len(content) < 500:
        reasons.append(f"字数不足：{len(content)} < 500")
    if len(re.findall(r"^##\s", content, re.MULTILINE)) < 3:
        reasons.append("H2 标题不足 < 3")
    missing = [k for k in ["需求", "功能", "用户"] if k not in content]
    if missing:
        reasons.append(f"缺少关键词：{missing}")
    return {"pass": not reasons, "reasons": reasons}

def validate_code(content: str, language: str) -> Dict[str, Any]:
    reasons = []
    try:
        if language == "py":
            tree = ast.parse(content)
            defs = [n for n in ast.walk(tree)
                    if isinstance(n, (ast.FunctionDef, ast.ClassDef))]
        else:
            defs = re.findall(r"(function\s+\w+|class\s+\w+|=>\s*{)", content)
        if len(defs) < 2:
            reasons.append(f"函数/类定义不足：{len(defs)} < 2")
        if len(content.strip()) < 50:
            reasons.append("实现过于简单（疑似空壳）")
    except SyntaxError as e:
        reasons.append(f"语法错误：{e}")
    return {"pass": not reasons, "reasons": reasons}

def validate_json_schema(content: str) -> Dict[str, Any]:
    reasons = []
    try:
        data = json.loads(content) if content.strip().startswith("{") else yaml.safe_load(content)
        if not isinstance(data, dict):
            reasons.append("顶层不是对象")
            return {"pass": False, "reasons": reasons}
        missing = [f for f in ["name", "endpoints"] if f not in data]
        if missing:
            reasons.append(f"缺少必填字段：{missing}")
    except Exception as e:
        reasons.append(f"解析失败：{e}")
    return {"pass": not reasons, "reasons": reasons}

VALIDATORS = {
    "sql": validate_sql, "md": validate_md, "json": validate_json_schema,
    "yaml": validate_json_schema,
    "py": lambda c: validate_code(c, "py"),
    "js": lambda c: validate_code(c, "js"),
    "ts": lambda c: validate_code(c, "js"),
}

async def validate_milestone_artifact(milestone_id: int, filename: str, content: bytes):
    ms = models.get_milestone(milestone_id)
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "other"
    text = content.decode("utf-8", errors="ignore")
    validator = VALIDATORS.get(ext)
    llm_used = False
    if validator:
        result = validator(text)
    else:
        result = client.validate_with_llm(ms["name"], ext, text)
        llm_used = True
    fail_reasons = json.dumps(result.get("reasons", []), ensure_ascii=False)
    models.insert_validation(
        milestone_id, filename, ext,
        "pass" if result.get("pass") else "fail",
        fail_reasons, llm_used)
    if result.get("pass"):
        models.update_milestone_status(milestone_id, MilestoneStatus.DONE.value)
    else:
        models.update_milestone_status(milestone_id, MilestoneStatus.LOCKED.value)
    return result

def can_proceed_to_next(project_id: int, current_milestone_id: int) -> bool:
    return models.get_milestone(current_milestone_id)["status"] == MilestoneStatus.DONE.value
```

- [ ] **步骤 4：运行测试通过**

`pytest tests/test_validate_sql.py -v` → 3 PASS。

- [ ] **步骤 5：routes/validate.py**

```python
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services import validate_service

router = APIRouter()

@router.post("/api/validate/{milestone_id}")
async def validate(milestone_id: int, file: UploadFile = File(...)):
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件超过 10MB")
    return await validate_service.validate_milestone_artifact(milestone_id, file.filename, content)
```

- [ ] **步骤 6：修改 routes/__init__.py 和 main.py**

`routes/__init__.py`:
```python
from app.routes import projects, validate
```

`main.py` 增加：
```python
from app.routes import validate
app.include_router(validate.router)
```

- [ ] **步骤 7：test_lock_milestone.py（闭环测试）**

```python
import pytest
from unittest.mock import patch
from app.services import project_service, validate_service
from app import models
from app.state_machine import MilestoneStatus

FALLBACK_PLAN = {
    "milestones": [
        {"name": "数据库", "expected_artifact_type": "sql", "tasks": [
            {"title": "建表", "priority": "core", "est_effort_days": 1.0, "week": 1}]},
        {"name": "实现", "expected_artifact_type": "code", "tasks": [
            {"title": "API", "priority": "core", "est_effort_days": 2.0, "week": 2}]}]}

VALID_SQL = """
CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT);
CREATE TABLE orders (id INTEGER PRIMARY KEY, user_id INTEGER, FOREIGN KEY (user_id) REFERENCES users(id));
"""
EMPTY_SQL = "-- nothing"

@patch("app.services.project_service.client.generate_initial_plan", return_value=FALLBACK_PLAN)
@pytest.mark.asyncio
async def test_lock_then_unlock(mock_llm):
    pid = project_service.create_project_with_plan("p", "2026-08-20", 3, "topic")
    ms_id = models.list_milestones(pid)[0]["id"]
    r = await validate_service.validate_milestone_artifact(ms_id, "empty.sql", EMPTY_SQL.encode())
    assert r["pass"] is False
    assert models.get_milestone(ms_id)["status"] == MilestoneStatus.LOCKED.value
    r = await validate_service.validate_milestone_artifact(ms_id, "valid.sql", VALID_SQL.encode())
    assert r["pass"] is True
    assert models.get_milestone(ms_id)["status"] == MilestoneStatus.DONE.value
    assert validate_service.can_proceed_to_next(pid, ms_id) is True
```

- [ ] **步骤 8：运行测试**

`pytest tests/test_lock_milestone.py tests/test_validate_sql.py -v` → 4 PASS。

- [ ] **步骤 9：Commit**

```bash
git add backend/app/services/validate_service.py backend/app/routes/validate.py backend/app/main.py backend/app/routes/__init__.py backend/tests/test_validate_sql.py backend/tests/test_lock_milestone.py
git commit -m "feat: 突出点① 实体验证（5 类校验 + locked 机制）"
```

---

## 任务 5：重规划后端（突出点②）

【用户视角】POST /api/replan/{pid}/propose 返回缺口和 LLM 砍/降级提案；POST /api/replan/{pid}/apply 应用提案（铁律：只能砍 optional）；POST /api/replan/{pid}/trigger_overdue 手动模拟偏航（Demo 用）。

**文件：** 创建 `backend/app/services/replan_service.py`、`backend/app/routes/replan.py`、`backend/tests/test_replan.py`
修改：`backend/app/main.py`、`backend/app/routes/__init__.py`

- [ ] **步骤 1：test_replan.py（先红）**

```python
import pytest
from unittest.mock import patch
from app.services import project_service, replan_service
from app import models
from app.state_machine import TaskStatus

FALLBACK_PLAN = {
    "milestones": [
        {"name": "M1", "expected_artifact_type": "md", "tasks": [
            {"title": "core task", "priority": "core", "est_effort_days": 3.0, "week": 1},
            {"title": "opt task A", "priority": "optional", "est_effort_days": 2.0, "week": 1},
            {"title": "opt task B", "priority": "optional", "est_effort_days": 1.0, "week": 1}]}]}

@patch("app.services.project_service.client.generate_initial_plan", return_value=FALLBACK_PLAN)
def test_capacity_calc_no_gap(mock_llm):
    pid = project_service.create_project_with_plan("p", "2026-12-31", 3, "t")
    tasks = models.list_tasks_by_project(pid)
    gap = replan_service.calculate_gap(tasks, remaining_days=60, team_size=3)
    assert gap <= 0

@patch("app.services.project_service.client.generate_initial_plan", return_value=FALLBACK_PLAN)
def test_capacity_calc_with_gap(mock_llm):
    pid = project_service.create_project_with_plan("p", "2026-12-31", 3, "t")
    tasks = models.list_tasks_by_project(pid)
    gap = replan_service.calculate_gap(tasks, remaining_days=1, team_size=1)
    assert gap > 0

@patch("app.services.project_service.client.generate_initial_plan", return_value=FALLBACK_PLAN)
@patch("app.services.replan_service.client.generate_replan_proposal")
def test_replan_cannot_cut_core(mock_proposal, mock_init):
    """铁律：即使 LLM 试图砍 core，系统也不允许"""
    pid = project_service.create_project_with_plan("p", "2026-12-31", 3, "t")
    tasks = models.list_tasks_by_project(pid)
    core_id = [t for t in tasks if t["priority"] == "core"][0]["id"]
    mock_proposal.return_value = {
        "cut_tasks": [core_id], "downgrade_tasks": [], "rationale": "wrong"}
    proposal = replan_service.propose_replan(pid, remaining_days=1, team_size=1)
    replan_service.apply_replan(pid, proposal["proposal"])
    assert models.get_task(core_id)["status"] != "cut"
    cut_tasks = [t for t in models.list_tasks_by_project(pid, include_cut=True)
                 if t["status"] == "cut"]
    assert len(cut_tasks) >= 1
    assert all(t["priority"] == "optional" for t in cut_tasks)
```

- [ ] **步骤 2：运行验证失败**

`pytest tests/test_replan.py -v` → FAIL，模块不存在。

- [ ] **步骤 3：replan_service.py**

```python
import json
from datetime import datetime, timedelta
from app import models
from app.llm import client
from app.state_machine import TaskStatus, transition_task, ProjectStatus

EFFICIENCY_FACTOR = 0.6

def calculate_gap(tasks, remaining_days, team_size):
    remaining_work = sum(t["est_effort_days"] for t in tasks
                         if t["status"] in ("planned", "doing", "overdue"))
    capacity = remaining_days * team_size * EFFICIENCY_FACTOR
    return round(remaining_work - capacity, 2)

def propose_replan(project_id, remaining_days, team_size):
    tasks = models.list_tasks_by_project(project_id)
    gap = calculate_gap(tasks, remaining_days, team_size)
    if gap <= 0:
        return {"gap_days": gap, "proposal": None, "action": "no_action",
                "message": "产能充足，无需砍需求"}
    project = models.get_project(project_id)
    if project["status"] != ProjectStatus.CRISIS.value:
        models.update_project_status(project_id, ProjectStatus.CRISIS.value)
    tasks_for_llm = [{"id": t["id"], "title": t["title"], "priority": t["priority"],
                      "difficulty": t["difficulty"],
                      "est_effort_days": t["est_effort_days"],
                      "status": t["status"]} for t in tasks]
    proposal = client.generate_replan_proposal(
        remaining_days, team_size, gap,
        json.dumps(tasks_for_llm, ensure_ascii=False))
    models.insert_replan_log(project_id, gap,
                              json.dumps(proposal, ensure_ascii=False), False)
    return {"gap_days": gap, "proposal": proposal, "action": "propose",
            "message": f"缺口 {gap} 人天，已生成砍/降级提案"}

def apply_replan(project_id, proposal):
    if not proposal:
        return {"applied": False, "message": "无提案可应用"}
    cut_ids = proposal.get("cut_tasks", [])
    downgrade = proposal.get("downgrade_tasks", [])
    valid_cuts = []
    for tid in cut_ids:
        task = models.get_task(tid)
        if task and task["priority"] == "optional":
            new_status = transition_task(TaskStatus(task["status"]), "cut")
            models.update_task_status(tid, new_status.value)
            valid_cuts.append(tid)
    for d in downgrade:
        tid = d.get("id")
        task = models.get_task(tid)
        if not task:
            continue
        models.update_task(tid,
                           difficulty=d.get("to", task["difficulty"]),
                           est_effort_days=d.get("new_effort", task["est_effort_days"] * 0.6))
    # 保底：若仍有缺口，强制砍难度最高的 optional
    project = models.get_project(project_id)
    deadline_dt = datetime.fromisoformat(project["deadline"])
    remaining_days = max(0, (deadline_dt - datetime.now()).days)
    remaining_tasks = models.list_tasks_by_project(project_id)
    gap = calculate_gap(remaining_tasks, remaining_days, project["team_size"])
    if gap > 0:
        optional_undoing = [t for t in remaining_tasks
                            if t["priority"] == "optional"
                            and t["status"] in ("planned", "doing", "overdue")]
        if optional_undoing:
            optional_undoing.sort(key=lambda t: t["est_effort_days"], reverse=True)
            t = optional_undoing[0]
            new_status = transition_task(TaskStatus(t["status"]), "cut")
            models.update_task_status(t["id"], new_status.value)
            valid_cuts.append(t["id"])
    # 重排剩余任务日期
    remaining = models.list_tasks_by_project(project_id)
    remaining.sort(key=lambda t: t.get("due_date") or "")
    today = datetime.now()
    n = max(1, len(remaining))
    for i, t in enumerate(remaining):
        new_due = today + timedelta(days=(i + 1) * max(1, remaining_days // n))
        models.update_task(t["id"], due_date=new_due.isoformat())
    models.update_project_status(project_id, ProjectStatus.ACTIVE.value)
    models.insert_replan_log(project_id, gap,
                              json.dumps(proposal, ensure_ascii=False), True)
    return {"applied": True, "cut_task_ids": valid_cuts,
            "downgrade_count": len(downgrade), "remaining_gap": gap}
```

- [ ] **步骤 4：运行测试通过**

`pytest tests/test_replan.py -v` → 3 PASS。

- [ ] **步骤 5：routes/replan.py**

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
from app.services import replan_service
from app import models
from app.db import get_conn

router = APIRouter()

class ReplanApply(BaseModel):
    proposal: dict

@router.post("/api/replan/{pid}/propose")
def propose(pid: int):
    project = models.get_project(pid)
    if not project:
        raise HTTPException(404, "项目不存在")
    deadline_dt = datetime.fromisoformat(project["deadline"])
    remaining_days = max(0, (deadline_dt - datetime.now()).days)
    return replan_service.propose_replan(pid, remaining_days, project["team_size"])

@router.post("/api/replan/{pid}/apply")
def apply(pid: int, req: ReplanApply):
    return replan_service.apply_replan(pid, req.proposal)

@router.post("/api/replan/{pid}/trigger_overdue")
def trigger_overdue(pid: int):
    """手动将 doing 任务标记为 overdue（Demo 模拟偏航用）"""
    with get_conn() as conn:
        conn.execute(
            "UPDATE tasks SET status='overdue' WHERE project_id=? AND status='doing'",
            (pid,))
    return {"message": "已将所有 doing 任务标记为 overdue"}
```

- [ ] **步骤 6：修改 routes/__init__.py 和 main.py**

`routes/__init__.py`:
```python
from app.routes import projects, validate, replan
```

`main.py` 增加：
```python
from app.routes import replan
app.include_router(replan.router)
```

- [ ] **步骤 7：Commit**

```bash
git add backend/app/services/replan_service.py backend/app/routes/replan.py backend/app/main.py backend/app/routes/__init__.py backend/tests/test_replan.py
git commit -m "feat: 突出点② 动态重算（产能计算 + LLM 提案 + 铁律校验）"
```

---

## 任务 6：主动打扰后端（突出点③）

【用户视角】POST /api/notify/test 手动触发飞书推送（Demo 主路径）；APScheduler 定时扫描逾期任务并推送；GET /api/notifications 查通知日志。

**文件：** 创建 `backend/app/services/notify_service.py`、`backend/app/routes/notify.py`、`backend/tests/test_notify_mock.py`
修改：`backend/app/main.py`、`backend/app/routes/__init__.py`

- [ ] **步骤 1：notify_service.py**

```python
import hashlib
import hmac
import base64
import time
import json
import logging
import httpx
from apscheduler.schedulers.background import BackgroundScheduler
from app import config, models

logger = logging.getLogger(__name__)
_scheduler: BackgroundScheduler = None

def _sign_feishu(secret: str):
    timestamp = str(int(time.time()))
    string_to_sign = f"{timestamp}\n{secret}"
    hmac_code = hmac.new(string_to_sign.encode("utf-8"), digestmod=hashlib.sha256).digest()
    return timestamp, base64.b64encode(hmac_code).decode("utf-8")

def send_feishu(text: str, project_id: int = None, msg_type: str = "manual_test") -> dict:
    if not config.FEISHU_WEBHOOK_URL:
        logger.warning("未配置 FEISHU_WEBHOOK_URL，跳过推送")
        result = {"status": "failed", "response": "webhook 未配置"}
        models.insert_notification(project_id, msg_type, text, "failed",
                                    json.dumps(result, ensure_ascii=False))
        return result
    payload = {"msg_type": "text", "content": {"text": text}}
    if config.FEISHU_SECRET:
        ts, sign = _sign_feishu(config.FEISHU_SECRET)
        payload["timestamp"] = ts
        payload["sign"] = sign
    try:
        resp = httpx.post(config.FEISHU_WEBHOOK_URL, json=payload, timeout=10)
        resp_data = resp.json()
        status = "sent" if resp.status_code == 200 and resp_data.get("StatusCode", 0) == 0 else "failed"
        result = {"status": status, "response": json.dumps(resp_data, ensure_ascii=False)}
    except Exception as e:
        logger.error(f"飞书推送失败: {e}")
        result = {"status": "failed", "response": str(e)}
    models.insert_notification(project_id, msg_type, text, result["status"],
                                result.get("response", ""))
    return result

def scan_and_notify_overdue():
    """定时扫描逾期任务并推送"""
    overdue = models.list_overdue_tasks()
    if not overdue:
        return {"scanned": 0, "notified": 0}
    by_project = {}
    for t in overdue:
        by_project.setdefault(t["project_id"], []).append(t)
    for pid, tasks in by_project.items():
        lines = [f"⚠️ 项目有 {len(tasks)} 个任务逾期："]
        for t in tasks[:5]:
            lines.append(f"· 《{t['title']}》状态={t['status']}")
        send_feishu("\n".join(lines), project_id=pid, msg_type="overdue")
    return {"scanned": len(overdue), "notified": len(by_project)}

def start_scheduler():
    global _scheduler
    if _scheduler is not None:
        return
    _scheduler = BackgroundScheduler()
    _scheduler.add_job(scan_and_notify_overdue, "interval",
                       minutes=config.SCHEDULER_INTERVAL_MINUTES, id="scan_overdue")
    _scheduler.start()

def stop_scheduler():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
```

- [ ] **步骤 2：routes/notify.py**

```python
from fastapi import APIRouter
from app.services import notify_service
from app import models

router = APIRouter()

@router.post("/api/notify/test")
def test_notify(project_id: int = None):
    """手动推送测试消息（Demo 主路径）"""
    text = f"【CoreCompass 测试通知】项目 ID={project_id} 的 Agent 正在主动联系你，请关注任务进度。"
    return notify_service.send_feishu(text, project_id=project_id, msg_type="manual_test")

@router.post("/api/notify/scan")
def manual_scan():
    return notify_service.scan_and_notify_overdue()

@router.get("/api/notifications")
def list_notifications(project_id: int = None, limit: int = 50):
    return models.list_notifications(project_id, limit)
```

- [ ] **步骤 3：修改 routes/__init__.py 和 main.py**

`routes/__init__.py`:
```python
from app.routes import projects, validate, replan, notify
```

`main.py` 增加（在 startup 中启动调度器）：
```python
from app.routes import notify
app.include_router(notify.router)

from app.services import notify_service
@app.on_event("startup")
def start_sched():
    notify_service.start_scheduler()

@app.on_event("shutdown")
def stop_sched():
    notify_service.stop_scheduler()
```

- [ ] **步骤 4：test_notify_mock.py（mock httpx）**

```python
import pytest
from unittest.mock import patch, MagicMock
from app.services import notify_service
from app import models, config

def test_send_feishu_no_webhook_configured(monkeypatch):
    monkeypatch.setattr(config, "FEISHU_WEBHOOK_URL", "")
    result = notify_service.send_feishu("test", project_id=None)
    assert result["status"] == "failed"
    assert models.list_notifications(limit=1)[0]["status"] == "failed"

def test_send_feishu_success(monkeypatch):
    monkeypatch.setattr(config, "FEISHU_WEBHOOK_URL", "https://example.com/hook")
    monkeypatch.setattr(config, "FEISHU_SECRET", "")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"StatusCode": 0, "msg": "ok"}
    with patch("app.services.notify_service.httpx.post", return_value=mock_resp):
        result = notify_service.send_feishu("hello", project_id=None)
    assert result["status"] == "sent"
    assert models.list_notifications(limit=1)[0]["status"] == "sent"

def test_send_feishu_network_error(monkeypatch):
    monkeypatch.setattr(config, "FEISHU_WEBHOOK_URL", "https://example.com/hook")
    with patch("app.services.notify_service.httpx.post", side_effect=Exception("timeout")):
        result = notify_service.send_feishu("hello", project_id=None)
    assert result["status"] == "failed"
```

- [ ] **步骤 5：运行测试**

`pytest tests/test_notify_mock.py -v` → 3 PASS。

- [ ] **步骤 6：Commit**

```bash
git add backend/app/services/notify_service.py backend/app/routes/notify.py backend/app/main.py backend/app/routes/__init__.py backend/tests/test_notify_mock.py
git commit -m "feat: 突出点③ 主动打扰（飞书 webhook + APScheduler + 手动触发）"
```

---

## 任务 7：前端骨架（项目创建 + 任务看板 + 上传区）

【用户视角】浏览器打开首页 → 看到创建项目表单 → 提交后看到任务看板（按里程碑分组）和里程碑上传区。三页主路径走通。

**文件：** 创建 `frontend/static/components/{project-create,task-board,upload-panel}.js`
修改：`frontend/index.html`、`frontend/static/app.js`、`frontend/static/style.css`

- [ ] **步骤 1：app.js（主组件 + 状态管理）**

```javascript
function app() {
  return {
    view: 'create',
    project: null, milestones: [], tasks: [], notifications: [],

    async createProject(form) {
      const r = await fetch('/api/projects', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(form)
      });
      const data = await r.json();
      this.project = data.detail.project;
      this.milestones = data.detail.milestones;
      this.tasks = data.detail.tasks;
      this.view = 'board';
    },

    async loadProject(pid) {
      const r = await fetch(`/api/projects/${pid}`);
      const data = await r.json();
      this.project = data.project;
      this.milestones = data.milestones;
      this.tasks = data.tasks;
      this.view = 'board';
    },

    async triggerOverdue() {
      await fetch(`/api/replan/${this.project.id}/trigger_overdue`, {method: 'POST'});
      await this.loadProject(this.project.id);
    },

    async refresh() {
      if (this.project) await this.loadProject(this.project.id);
    }
  }
}
```

- [ ] **步骤 2：components/project-create.js**

```javascript
function projectCreate(parent) {
  return {
    form: {name: '', deadline: '', team_size: 3, topic_desc: ''},
    submitting: false,
    async submit() {
      this.submitting = true;
      try { await parent.createProject(this.form); }
      finally { this.submitting = false; }
    }
  }
}
```

- [ ] **步骤 3：components/task-board.js**

```javascript
function taskBoard(parent) {
  return {
    groupByMilestone() {
      const map = {};
      for (const t of parent.tasks) {
        if (!map[t.milestone_id]) map[t.milestone_id] = [];
        map[t.milestone_id].push(t);
      }
      return parent.milestones.map(m => ({milestone: m, tasks: map[m.id] || []}));
    },
    statusLabel(s) {
      return {planned:'待开始',doing:'进行中',done:'已完成',overdue:'已逾期',cut:'已砍'}[s] || s;
    },
    priorityLabel(p) { return {core:'核心',optional:'可选'}[p] || p; }
  }
}
```

- [ ] **步骤 4：components/upload-panel.js**

```javascript
function uploadPanel(parent) {
  return {
    uploading: false,
    lastResult: null,
    async upload(milestoneId, fileEl) {
      const file = fileEl.files[0];
      if (!file) return;
      this.uploading = true;
      const fd = new FormData();
      fd.append('file', file);
      try {
        const r = await fetch(`/api/validate/${milestoneId}`, {method: 'POST', body: fd});
        this.lastResult = await r.json();
        await parent.refresh();
      } finally { this.uploading = false; }
    }
  }
}
```

- [ ] **步骤 5：修改 index.html 接入三面板**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <title>CoreCompass · 校园项目粉碎机</title>
  <link rel="stylesheet" href="/static/style.css">
  <script defer src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js"></script>
</head>
<body>
  <header><h1>CoreCompass</h1><p>校园项目"伪需求"粉碎机</p></header>
  <main x-data="app()">
    <!-- 创建项目 -->
    <template x-if="view === 'create'">
      <div x-data="projectCreate($data)" class="panel">
        <h2>创建项目</h2>
        <form @submit.prevent="submit()">
          <label>项目名<input x-model="form.name" required></label>
          <label>截止日期<input type="date" x-model="form.deadline" required></label>
          <label>团队人数<input type="number" x-model.number="form.team_size" min="1" max="10"></label>
          <label>课题描述<textarea x-model="form.topic_desc" rows="4" required></textarea></label>
          <button :disabled="submitting">生成拆解计划</button>
        </form>
      </div>
    </template>

    <!-- 任务看板 + 上传区 -->
    <template x-if="view === 'board'">
      <div>
        <div class="project-header">
          <h2 x-text="project?.name"></h2>
          <span class="badge" x-text="project?.status"></span>
          <button @click="triggerOverdue()">模拟偏航（标记 doing 为逾期）</button>
        </div>

        <div x-data="taskBoard($data)" class="board">
          <template x-for="g in groupByMilestone()" :key="g.milestone.id">
            <div class="milestone-card">
              <h3 x-text="g.milestone.name"></h3>
              <span class="badge" x-text="g.milestone.status"></span>
              <ul>
                <template x-for="t in g.tasks" :key="t.id">
                  <li>
                    <span x-text="t.title"></span>
                    <span class="tag" x-text="statusLabel(t.status)"></span>
                    <span class="tag" x-text="priorityLabel(t.priority)"></span>
                  </li>
                </template>
              </ul>
              <!-- 上传区 -->
              <div x-data="uploadPanel($root)">
                <input type="file" :id="'file-'+g.milestone.id">
                <button @click="upload(g.milestone.id, $el.previousElementSibling)" :disabled="uploading">上传验收</button>
                <div x-show="lastResult" :class="lastResult?.pass ? 'pass' : 'fail'">
                  <span x-text="lastResult?.pass ? '✓ 通过，解锁下一阶段' : '✗ 未通过'"></span>
                  <ul x-show="lastResult?.reasons?.length">
                    <template x-for="r in lastResult?.reasons || []">
                      <li x-text="r"></li>
                    </template>
                  </ul>
                </div>
              </div>
            </div>
          </template>
        </div>
      </div>
    </template>
  </main>
  <script src="/static/app.js"></script>
  <script src="/static/components/project-create.js"></script>
  <script src="/static/components/task-board.js"></script>
  <script src="/static/components/upload-panel.js"></script>
</body>
</html>
```

- [ ] **步骤 6：补 style.css（看板样式）**

追加：
```css
.panel { background: white; padding: 24px; border-radius: 8px; max-width: 600px; }
.panel form { display: flex; flex-direction: column; gap: 12px; }
.panel label { display: flex; flex-direction: column; gap: 4px; font-size: 14px; }
.project-header { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }
.badge { background: #e8eef7; padding: 2px 8px; border-radius: 4px; font-size: 12px; }
.board { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px; }
.milestone-card { background: white; padding: 16px; border-radius: 8px; border-left: 4px solid #1a2b4a; }
.milestone-card h3 { margin: 0 0 8px; }
.milestone-card ul { list-style: none; padding: 0; margin: 8px 0; }
.milestone-card li { padding: 4px 0; display: flex; gap: 8px; align-items: center; }
.tag { background: #f0f0f0; padding: 1px 6px; border-radius: 3px; font-size: 11px; }
.pass { color: #16a34a; margin-top: 8px; }
.fail { color: #dc2626; margin-top: 8px; }
button { background: #1a2b4a; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; }
button:disabled { opacity: 0.5; }
```

- [ ] **步骤 7：手动验证主路径**

启动后端，浏览器访问 http://localhost:8000：
1. 填表创建项目（如"二手平台 / 2026-08-20 / 3 / 校园二手交易平台"）→ 应跳转到任务看板，看到 4 个里程碑卡片，每卡片有任务和上传区
2. 在某里程碑上传 `empty.sql`（内容 `-- nothing`）→ 应显示红色"✗ 未通过：缺少外键"
3. 上传合规 .sql → 应显示绿色"✓ 通过"

- [ ] **步骤 8：Commit**

```bash
git add frontend/
git commit -m "feat: 前端骨架（项目创建 + 任务看板 + 上传验收）"
```

---

## 任务 8：前端补全（重规划模态 + 通知日志 + 打卡）

【用户视角】看板支持任务打卡（更新状态）；点"触发重规划"→ 弹出模态显示缺口和提案→ 确认后任务被砍/降级，看板实时刷新；通知日志面板展示飞书推送记录。

**文件：** 创建 `frontend/static/components/{replan-modal,notify-log}.py`
修改：`backend/app/routes/tasks.py`（新建，打卡 API）、`backend/app/main.py`、`backend/app/routes/__init__.py`、`frontend/index.html`、`frontend/static/app.js`

- [ ] **步骤 1：routes/tasks.py（打卡 + 状态更新 API）**

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app import models
from app.state_machine import TaskStatus, transition_task, InvalidTransition
from datetime import datetime

router = APIRouter()

class CheckinReq(BaseModel):
    note: str = ""

class StatusUpdate(BaseModel):
    event: str  # start | complete | overdue

@router.post("/api/tasks/{task_id}/checkin")
def checkin(task_id: int, req: CheckinReq):
    models.insert_checkin(task_id, req.note)
    return {"ok": True}

@router.patch("/api/tasks/{task_id}/status")
def update_status(task_id: int, req: StatusUpdate):
    task = models.get_task(task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    try:
        new_status = transition_task(TaskStatus(task["status"]), req.event)
    except InvalidTransition as e:
        raise HTTPException(400, str(e))
    completed_at = datetime.now().isoformat() if new_status == TaskStatus.DONE else None
    models.update_task_status(task_id, new_status.value, completed_at)
    return {"task_id": task_id, "status": new_status.value}
```

- [ ] **步骤 2：修改 routes/__init__.py 和 main.py 注册 tasks 路由**

`routes/__init__.py`:
```python
from app.routes import projects, validate, replan, notify, tasks
```

`main.py` 增加：
```python
from app.routes import tasks
app.include_router(tasks.router)
```

- [ ] **步骤 3：components/replan-modal.js**

```javascript
function replanModal(parent) {
  return {
    open: false,
    loading: false,
    proposal: null,
    gapDays: null,
    applying: false,
    result: null,

    async propose() {
      this.open = true;
      this.loading = true;
      this.proposal = null;
      try {
        const r = await fetch(`/api/replan/${parent.project.id}/propose`, {method: 'POST'});
        const data = await r.json();
        this.gapDays = data.gap_days;
        this.proposal = data.proposal;
      } finally { this.loading = false; }
    },

    async apply() {
      if (!this.proposal) return;
      this.applying = true;
      try {
        const r = await fetch(`/api/replan/${parent.project.id}/apply`, {
          method: 'POST', headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({proposal: this.proposal})
        });
        this.result = await r.json();
        await parent.refresh();
        this.open = false;
      } finally { this.applying = false; }
    }
  }
}
```

- [ ] **步骤 4：components/notify-log.js**

```javascript
function notifyLog(parent) {
  return {
    logs: [],
    async load() {
      const r = await fetch('/api/notifications?limit=20');
      this.logs = await r.json();
    },
    async testPush() {
      await fetch(`/api/notify/test?project_id=${parent.project?.id || ''}`, {method: 'POST'});
      await this.load();
    },
    init() { this.load(); }
  }
}
```

- [ ] **步骤 5：app.js 增加状态切换方法**

在 app() 中追加：
```javascript
async updateTaskStatus(taskId, event) {
  await fetch(`/api/tasks/${taskId}/status`, {
    method: 'PATCH', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({event})
  });
  await this.loadProject(this.project.id);
}
```

- [ ] **步骤 6：index.html 接入重规划模态 + 通知日志**

在 `view === 'board'` 模板内的 `project-header` 后添加按钮：
```html
<button @click="$root._replan.propose()">触发重规划</button>
```

在 `<main>` 末尾、`</main>` 前添加：
```html
<!-- 重规划模态 -->
<div x-data="replanModal($data)" x-init="_replan = this" x-show="open" class="modal-overlay" @click.self="open=false">
  <div class="modal">
    <h3>动态重算 · 砍需求提案</h3>
    <template x-if="loading"><p>AI 分析中...</p></template>
    <template x-if="!loading && proposal">
      <div>
        <p>缺口：<strong x-text="gapDays"></strong> 人天</p>
        <p x-text="proposal.rationale"></p>
        <div x-show="proposal.cut_tasks?.length">
          <p>建议砍掉的任务 ID：<span x-text="proposal.cut_tasks?.join(', ')"></span></p>
        </div>
        <div x-show="proposal.downgrade_tasks?.length">
          <p>建议降级的任务：
            <template x-for="d in proposal.downgrade_tasks" :key="d.id">
              <span x-text="`#${d.id} ${d.from}→${d.to}`"></span>
            </template>
          </p>
        </div>
        <button @click="apply()" :disabled="applying">确认应用</button>
        <button @click="open=false">取消</button>
      </div>
    </template>
  </div>
</div>

<!-- 通知日志 -->
<div x-data="notifyLog($data)" x-init="init()" class="panel" style="margin-top:24px">
  <h3>通知日志 <button @click="testPush()">测试推送飞书</button></div>
  <ul>
    <template x-for="log in logs" :key="log.id">
      <li :class="log.status">
        <span x-text="log.created_at"></span>
        <span x-text="log.type"></span>
        <span x-text="log.status"></span>
        <p x-text="log.content"></p>
      </li>
    </template>
  </ul>
</div>
```

- [ ] **步骤 7：补 style.css（模态 + 日志样式）**

追加：
```css
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 100; }
.modal { background: white; padding: 24px; border-radius: 8px; max-width: 500px; width: 90%; }
.modal h3 { margin-top: 0; }
.notify-log ul { list-style: none; padding: 0; }
.notify-log li { padding: 8px 0; border-bottom: 1px solid #eee; }
.notify-log li.sent { color: #16a34a; }
.notify-log li.failed { color: #dc2626; }
```

- [ ] **步骤 8：手动验证三突出点闭环**

启动后端，端到端走查：
1. 创建项目 → 看到任务看板
2. 上传空 .sql → locked 红色提示；上传合规 .sql → 通过绿色（突出点①）
3. 点"模拟偏航" → 任务标为 overdue；点"触发重规划" → 模态显示缺口+提案 → 确认 → 看板刷新，被砍任务消失（突出点②）
4. 点"测试推送飞书" → 飞书群收到消息，通知日志面板显示 sent（突出点③）

- [ ] **步骤 9：Commit**

```bash
git add backend/app/routes/tasks.py backend/app/routes/__init__.py backend/app/main.py frontend/
git commit -m "feat: 前端补全（重规划模态 + 通知日志 + 任务打卡）"
```

---

## 任务 9：集成测试 + Demo 走查 + bug 修

【用户视角】端到端 Demo 脚本能丝滑跑完三段式，所有边界情况（空文件/缺外键/砍 core 拒绝/飞书失败）都有预期行为。

**文件：** 补充 `backend/tests/test_e2e_demo.py`、`backend/tests/test_boundary.py`；修复走查发现的问题

- [ ] **步骤 1：test_e2e_demo.py（完整 Demo 流程测试）**

```python
import pytest
from unittest.mock import patch, MagicMock
from app.services import project_service, validate_service, replan_service, notify_service
from app import models, config
from app.state_machine import MilestoneStatus

FALLBACK_PLAN = {
    "milestones": [
        {"name": "数据库设计", "expected_artifact_type": "sql", "tasks": [
            {"title": "建表", "priority": "core", "est_effort_days": 1.0, "week": 1}]},
        {"name": "核心实现", "expected_artifact_type": "code", "tasks": [
            {"title": "后端 API", "priority": "core", "est_effort_days": 2.0, "week": 2},
            {"title": "前端页面", "priority": "optional", "est_effort_days": 1.5, "week": 2}]}]}

VALID_SQL = """
CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT);
CREATE TABLE orders (id INTEGER PRIMARY KEY, user_id INTEGER, FOREIGN KEY (user_id) REFERENCES users(id));
"""

@patch("app.services.project_service.client.generate_initial_plan", return_value=FALLBACK_PLAN)
@patch("app.services.notify_service.httpx.post")
@pytest.mark.asyncio
async def test_e2e_three_highlights(mock_post, mock_plan):
    """三段式 Demo 完整闭环"""
    mock_post.return_value = MagicMock(status_code=200, json=lambda: {"StatusCode": 0})

    # 段1：创建项目
    pid = project_service.create_project_with_plan("Demo", "2026-08-20", 3, "校园二手交易平台")
    assert len(models.list_tasks_by_project(pid)) == 3

    # 段2：突出点① 实体验证（先失败后通过）
    ms1 = models.list_milestones(pid)[0]
    r = await validate_service.validate_milestone_artifact(ms1["id"], "empty.sql", b"-- nothing")
    assert r["pass"] is False
    assert models.get_milestone(ms1["id"])["status"] == MilestoneStatus.LOCKED.value

    r = await validate_service.validate_milestone_artifact(ms1["id"], "valid.sql", VALID_SQL.encode())
    assert r["pass"] is True
    assert models.get_milestone(ms1["id"])["status"] == MilestoneStatus.DONE.value

    # 段3：突出点② 重规划（模拟偏航 + 应用提案）
    # 手动把一个 doing 任务标为 overdue
    tasks = models.list_tasks_by_project(pid)
    models.update_task_status(tasks[0]["id"], "doing")
    models.update_task_status(tasks[0]["id"], "overdue")
    # 设置很短的剩余时间触发缺口
    project = models.get_project(pid)
    proposal = replan_service.propose_replan(pid, remaining_days=1, team_size=1)
    assert proposal["gap_days"] > 0
    result = replan_service.apply_replan(pid, proposal["proposal"])
    assert result["applied"] is True
    # 至少砍了一个 optional
    cut = [t for t in models.list_tasks_by_project(pid, include_cut=True) if t["status"] == "cut"]
    assert len(cut) >= 1
    assert all(t["priority"] == "optional" for t in cut)

    # 段4：突出点③ 飞书推送
    r = notify_service.send_feishu("测试", project_id=pid, msg_type="manual_test")
    assert r["status"] == "sent"
    assert len(models.list_notifications(pid)) >= 1
```

- [ ] **步骤 2：test_boundary.py（边界情况）**

```python
import pytest
from app.services import validate_service

def test_sql_too_large_would_be_rejected_by_route():
    # 路由层有 10MB 限制，此处验证校验函数本身可处理大文本不崩
    big_sql = "CREATE TABLE a (id INTEGER PRIMARY KEY);\n" + "x" * 100000
    r = validate_service.validate_sql(big_sql)
    assert isinstance(r, dict) and "pass" in r

def test_md_validation_minimum():
    short_md = "# Title\n短"
    r = validate_service.validate_md(short_md)
    assert r["pass"] is False
    assert len(r["reasons"]) >= 2  # 字数 + H2 不足

def test_code_empty_file():
    r = validate_service.validate_code("", "py")
    assert r["pass"] is False

def test_json_invalid():
    r = validate_service.validate_json_schema("{not valid json")
    assert r["pass"] is False
    assert any("解析" in x for x in r["reasons"])
```

- [ ] **步骤 3：运行全部测试**

`pytest -v` → 全部 PASS（应在 25 个左右）。

- [ ] **步骤 4：手动 Demo 走查（按规格第九节脚本）**

按以下顺序在浏览器走一遍，记录任何卡顿/报错：
1. 创建"校园二手交易平台 / 2026-08-20 / 3 人"
2. 在"数据库设计"里程碑上传 `empty.sql`（内容 `-- nothing`）→ 期望红色"✗ 未通过：缺少外键"，里程碑状态显示 locked
3. 上传合规 .sql（含 2 表 + 主键 + 外键）→ 期望绿色"✓ 通过"
4. 点"模拟偏航" → 任务状态变 overdue
5. 点"触发重规划" → 模态显示缺口和提案
6. 点"确认应用" → 看板刷新，optional 任务被砍（消失），core 任务保留
7. 滚到底部通知日志 → 点"测试推送飞书" → 飞书群几秒内收到消息，日志面板显示 sent

- [ ] **步骤 5：修复走查发现的 bug**

逐一修复步骤 4 发现的问题。常见问题：
- LLM 返回 JSON 格式异常 → 已有 fallback，验证是否生效
- 飞书签名失败 → 检查 FEISHU_SECRET 配置
- 任务日期重排导致 due_date 早于今天 → 调整重排算法
- 前端 Alpine.js 响应式未触发 → 检查 `await parent.refresh()` 调用

- [ ] **步骤 6：Commit**

```bash
git add backend/tests/test_e2e_demo.py backend/tests/test_boundary.py
git commit -m "test: 端到端 Demo 测试 + 边界用例"
# bug 修复单独 commit
git add -A
git commit -m "fix: Demo 走查发现的问题修复"
```

---

## 任务 10：交付材料（录屏 + PPT + 详细材料）

【用户视角】三件交付物完成：MP4 录屏 ≤50MB、PPT ≤20MB、PDF 详细材料 ≤5MB，全部放在 `参赛材料/` 目录。

**文件：** 创建 `参赛材料/CoreCompass-录屏.mp4`、`参赛材料/CoreCompass-PPT.pptx`、`参赛材料/CoreCompass-详细材料.pdf`、`参赛材料/Demo脚本.md`

- [ ] **步骤 1：编写 Demo 脚本（用于录屏对照）**

`参赛材料/Demo脚本.md`:
```markdown
# CoreCompass Demo 脚本（5 分钟）

## 0:00-0:30 开场
- 作品名 + 一句话定位："校园项目伪需求粉碎机"
- 痛点：学生拿到大课题无从下手，AI 聊天工具只附和不把关

## 0:30-1:30 段1 项目拆解
- 输入"校园二手交易平台 / 30 天 / 3 人"
- 展示 LLM 生成的 4 里程碑 + 周任务计划

## 1:30-2:30 段2 突出点① 硬验收
- 上传空 .sql → 红色"缺少外键，进度锁定"
- 强调："Agent 不盲信用户，强制校验真实产物"
- 上传合规 .sql → 绿色通过，解锁下一阶段

## 2:30-3:30 段3 突出点② 动态重算
- 点"模拟偏航" → 任务标为逾期
- 点"触发重规划" → 显示缺口 + LLM 砍需求提案
- 强调铁律："只能砍 optional，core 只能降级"
- 确认 → 看板刷新，被砍任务划线消失

## 3:30-4:30 段4 突出点③ 主动打扰
- 点"测试推送飞书" → 切到飞书群画面 → 几秒内收到 Agent 催办消息
- 强调："Agent 不是被动唤醒，而是主动找人"

## 4:30-5:00 结尾
- 技术亮点：状态机 + 混合重规划（规则+LLM）+ 多类型文件校验 + 调度
- 落地价值：可推广到所有校园项目团队
```

- [ ] **步骤 2：录制 MP4（≤50MB）**

按 Demo 脚本录制：
- 工具：OBS 或 Windows 自带的"游戏栏"（Win+G）
- 分辨率：1280x720（控制文件大小）
- 时长：5 分钟以内
- 压缩：用 HandBrake 或 ffmpeg 压到 50MB 以下
  `ffmpeg -i input.mp4 -vcodec libx264 -crf 28 -preset slow -acodec aac -b:a 96k output.mp4`

- [ ] **步骤 3：编写 PPT 大纲（≤20MB）**

`参赛材料/CoreCompass-PPT.pptx`（10 页）：
1. 封面：作品名 + 团队 + Trae 校赛
2. 痛点：学生拿到大课题的困境（配图）
3. 解决方案：CoreCompass 三大突出点概览
4. 突出点①：硬验收（截图 + 反"AI 盲信"叙事）
5. 突出点②：动态重算（GPS 类比图 + 砍需求截图）
6. 突出点③：主动打扰（飞书通知截图）
7. 技术架构图（FastAPI + SQLite + APScheduler + 豆包）
8. 核心算法：状态机 + 重规划公式
9. Demo 截图（三段式）
10. 落地价值 + 未来扩展

- [ ] **步骤 4：编写详细材料（PDF，≤5MB）**

`参赛材料/CoreCompass-详细材料.pdf`（基于设计文档改写为面向评委的叙事）：
1. 目标用户与应用场景
2. 真实痛点与解决方案
3. 核心功能（三突出点详述）
4. 技术路线（架构图 + 关键算法）
5. 创新点（反 AI 盲信 / GPS 式重算 / 主动打扰）
6. 实际效果（Demo 截图）
7. 推广落地可行性

可先用 Markdown 写，再用 Typora/VS Code 转 PDF。

- [ ] **步骤 5：验证文件大小**

```bash
ls -lh 参赛材料/
```
确认：
- 录屏 MP4 ≤ 50MB
- PPT ≤ 20MB
- PDF ≤ 5MB

- [ ] **步骤 6：Commit**

```bash
git add 参赛材料/
git commit -m "docs: 添加参赛交付材料（录屏 + PPT + 详细材料 + Demo 脚本）"
```

---

## 计划自检（已执行）

**1. 规格覆盖度：**
- 三个突出点 → 任务 4（①）、任务 5（②）、任务 6（③） ✓
- 状态机 → 任务 1 ✓
- LLM 封装 + fallback → 任务 2 ✓
- 数据模型 6 表 → 任务 0 schema.sql + 任务 1 models.py ✓
- 错误处理（重试/JSON 修复/fallback/mock）→ 任务 2 + 任务 9 ✓
- 5 种文件校验 → 任务 4 ✓
- 铁律（只砍 optional）→ 任务 5 test_replan_cannot_cut_core ✓
- 飞书 webhook + 签名 → 任务 6 ✓
- APScheduler → 任务 6 ✓
- 手动触发按钮 → 任务 6 + 任务 8 ✓
- 降级表对应：fallback 模板（任务 2）、铁律保底（任务 5）、webhook 未配置时 failed（任务 6）✓
- Demo 脚本三段式 → 任务 9 + 任务 10 ✓
- 8 天排期 → 任务 0-10 对应 D1-D8 ✓

**2. 占位符扫描：** 无 TODO/待定，每个步骤有完整代码或明确命令。

**3. 类型一致性：**
- TaskStatus/MilestoneStatus/ProjectStatus 在任务 1 定义，后续任务引用一致 ✓
- transition_task/transition_milestone/transition_project 函数名全程一致 ✓
- models.* 函数名（create_project/list_tasks_by_project/update_task_status 等）跨任务一致 ✓
- LLM 函数名（generate_initial_plan/generate_replan_proposal/validate_with_llm）跨任务一致 ✓

**4. 已知简化（非缺陷，工期取舍）：**
- 前端组件用 Alpine.js CDN，无构建步骤，符合"solo 8 天"约束
- 测试覆盖 P0+P1，UI 交互靠手动走查（符合规格测试策略 P2 跳过）
- 飞书签名按官方 HMAC-SHA256 文档实现，未做完整回归测试（信任官方文档）

---

## 执行交接

计划已完成并保存到 `docs/superpowers/plans/2026-07-23-corecompass-implementation.md`。

**两种执行方式：**

1. **子代理驱动（推荐）** - 每个任务调度一个新的子代理，任务间进行审查，快速迭代
2. **内联执行** - 在当前会话中使用 executing-plans 执行任务，批量执行并设有检查点

**选哪种方式？**
