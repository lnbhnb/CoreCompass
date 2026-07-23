# 轻量协作版实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 为 CoreCompass 增加简单认证、多项目管理、任务认领与分配、任务审阅、成员进度视图，形成轻量协作版。

**架构：** 后端新增 users/project_members/invite_codes 三张表 + tasks 表加列，新增 auth/member/review 三个服务与路由，FastAPI 依赖注入做鉴权；前端 Alpine.js 扩展 5 个视图状态 + hash 路由 + 4 个新组件。

**技术栈：** Python 3.11+、FastAPI、sqlite3、hashlib.pbkdf2_hmac、secrets、Alpine.js 3.x

**对应规格：** `docs/superpowers/specs/2026-07-23-lightweight-collaboration-design.md`

**进度跟踪约定：** 每个任务头部【用户视角】= 该任务完成后你能看到什么效果。

---

## 文件结构

**新增：**
- `backend/app/services/auth_service.py` — 注册/登录/登出/加入，密码哈希，token 生成
- `backend/app/services/member_service.py` — 邀请码生成/校验，成员列表，进度统计
- `backend/app/services/review_service.py` — 任务提交/审阅/下载
- `backend/app/routes/auth.py` — 认证路由
- `backend/app/routes/members.py` — 成员与邀请路由
- `backend/app/routes/reviews.py` — 任务审阅路由
- `backend/app/deps.py` — FastAPI 依赖：get_current_user / require_member / require_leader
- `backend/tests/test_auth.py` / `test_permissions.py` / `test_task_review.py` / `test_invite.py`
- `frontend/static/components/auth.js` / `project-list.js` / `member-progress.js` / `task-assign.js`

**修改：**
- `backend/app/schema.sql` — 加 3 张新表
- `backend/app/db.py` — init_db 加 tasks/projects 字段迁移
- `backend/app/models.py` — 加 users/members/invites CRUD + tasks 新字段读写
- `backend/app/state_machine.py` — 加 ReviewStatus 枚举与 transition_review
- `backend/app/services/project_service.py` — create_project_with_plan 接收 creator_id
- `backend/app/routes/projects.py` / `tasks.py` — 加鉴权
- `backend/app/main.py` — 注册新路由
- `frontend/index.html` — 加 5 个视图模板
- `frontend/static/app.js` — hash 路由 + token 拦截器 + 鉴权状态
- `frontend/static/components/project-create.js` / `task-board.js` / `notify-log.js` — 适配
- `frontend/static/style.css` — 新视图样式

**迁移机制：** 新表加 schema.sql（`CREATE TABLE IF NOT EXISTS` 对新旧库都安全）。tasks/projects 加列用 `init_db()` 里 try-except 包裹 ALTER TABLE（SQLite 不支持 IF NOT EXISTS）。

---

## 任务 0：数据模型与迁移

【用户视角】后端启动后数据库自动有 users/members/invites 表，tasks 表有 assignee_id 等新字段，旧数据不丢。

**文件：**
- 修改：`backend/app/schema.sql`
- 修改：`backend/app/db.py`

- [ ] **步骤 1：在 schema.sql 末尾追加三张新表**

在 `backend/app/schema.sql` 末尾追加：

```sql
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  display_name TEXT NOT NULL,
  token TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS project_members (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role TEXT NOT NULL DEFAULT 'member',
  joined_at TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE(project_id, user_id)
);

CREATE TABLE IF NOT EXISTS invite_codes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  code TEXT NOT NULL UNIQUE,
  used_by_user_id INTEGER REFERENCES users(id),
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  expires_at TEXT NOT NULL
);
```

- [ ] **步骤 2：读 db.py 了解 init_db 现状**

运行：`Read backend/app/db.py`
预期：看到 `init_db()` 执行 `schema.sql` 的代码结构。

- [ ] **步骤 3：在 init_db 加 tasks/projects 加列迁移（幂等）**

修改 `backend/app/db.py` 的 `init_db()`，在 executescript schema 之后追加（conn 变量名按实际调整）：

```python
    _migrations = [
        "ALTER TABLE projects ADD COLUMN creator_id INTEGER REFERENCES users(id)",
        "ALTER TABLE tasks ADD COLUMN assignee_id INTEGER REFERENCES users(id)",
        "ALTER TABLE tasks ADD COLUMN review_status TEXT",
        "ALTER TABLE tasks ADD COLUMN submission_filename TEXT",
        "ALTER TABLE tasks ADD COLUMN submission_path TEXT",
        "ALTER TABLE tasks ADD COLUMN reviewed_by INTEGER REFERENCES users(id)",
        "ALTER TABLE tasks ADD COLUMN reviewed_at TEXT",
        "ALTER TABLE tasks ADD COLUMN review_comment TEXT",
    ]
    for sql in _migrations:
        try:
            conn.execute(sql)
        except Exception:
            pass  # 列已存在
    conn.commit()
```

- [ ] **步骤 4：确认现有测试未破坏**

运行：`pytest backend/tests/test_state_machine.py -v`
预期：PASS。

- [ ] **步骤 5：Commit**

```bash
git add backend/app/schema.sql backend/app/db.py
git commit -m "feat: 加 users/project_members/invite_codes 表与 tasks/projects 协作字段迁移"
```

---

## 任务 1：认证服务（注册/登录/登出）

【用户视角】后端能注册用户、登录拿 token、登出失效 token，密码用 PBKDF2 哈希存储。

**文件：**
- 创建：`backend/app/services/auth_service.py`
- 修改：`backend/app/models.py`
- 测试：`backend/tests/test_auth.py`

- [ ] **步骤 1：在 models.py 末尾追加 users CRUD**

在 `backend/app/models.py` 末尾追加：

```python
def create_user(username, password_hash, display_name, token):
    with db.get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO users(username, password_hash, display_name, token) VALUES(?,?,?,?)",
            (username, password_hash, display_name, token))
        return cur.lastrowid


def get_user_by_username(username):
    with db.get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        return dict(row) if row else None


def get_user_by_token(token):
    with db.get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE token=?", (token,)).fetchone()
        return dict(row) if row else None


def get_user(uid):
    with db.get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
        return dict(row) if row else None


def clear_user_token(uid):
    with db.get_conn() as conn:
        conn.execute("UPDATE users SET token=NULL WHERE id=?", (uid,))
```

- [ ] **步骤 2：编写失败测试 test_auth.py**

创建 `backend/tests/test_auth.py`：

```python
import pytest
from app.services import auth_service


def test_register_returns_user_and_token():
    result = auth_service.register("alice", "pw123", "爱丽丝")
    assert result["user"]["username"] == "alice"
    assert result["user"]["display_name"] == "爱丽丝"
    assert len(result["token"]) == 64


def test_register_duplicate_username_raises():
    auth_service.register("bob", "pw", "鲍勃")
    with pytest.raises(ValueError, match="用户名已存在"):
        auth_service.register("bob", "pw", "鲍勃2")


def test_login_correct_password_returns_token():
    auth_service.register("carol", "secret", "卡罗尔")
    result = auth_service.login("carol", "secret")
    assert result["user"]["username"] == "carol"
    assert len(result["token"]) == 64


def test_login_wrong_password_raises():
    auth_service.register("dave", "right", "戴夫")
    with pytest.raises(ValueError, match="用户名或密码错误"):
        auth_service.login("dave", "wrong")


def test_login_unknown_user_raises():
    with pytest.raises(ValueError, match="用户名或密码错误"):
        auth_service.login("nobody", "x")


def test_logout_clears_token():
    result = auth_service.register("eve", "pw", "伊芙")
    auth_service.logout(result["token"])
    from app import models
    assert models.get_user_by_token(result["token"]) is None


def test_password_not_stored_plaintext():
    auth_service.register("frank", "plaintext", "弗兰克")
    from app import models
    user = models.get_user_by_username("frank")
    assert "plaintext" not in user["password_hash"]
```

- [ ] **步骤 3：运行测试验证失败**

运行：`pytest backend/tests/test_auth.py -v`
预期：FAIL，`ModuleNotFoundError: app.services.auth_service`。

- [ ] **步骤 4：创建 auth_service.py**

创建 `backend/app/services/auth_service.py`：

```python
import hashlib
import secrets
from app import models, db


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
    return salt.hex() + ":" + dk.hex()


def _verify_password(password: str, stored: str) -> bool:
    salt_hex, dk_hex = stored.split(":")
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), 100000)
    return secrets.compare_digest(dk.hex(), dk_hex)


def register(username, password, display_name):
    if models.get_user_by_username(username):
        raise ValueError("用户名已存在")
    password_hash = _hash_password(password)
    token = secrets.token_hex(32)
    uid = models.create_user(username, password_hash, display_name, token)
    return {"user": {"id": uid, "username": username, "display_name": display_name}, "token": token}


def login(username, password):
    user = models.get_user_by_username(username)
    if not user or not _verify_password(password, user["password_hash"]):
        raise ValueError("用户名或密码错误")
    token = secrets.token_hex(32)
    with db.get_conn() as conn:
        conn.execute("UPDATE users SET token=? WHERE id=?", (token, user["id"]))
    return {"user": {"id": user["id"], "username": user["username"], "display_name": user["display_name"]}, "token": token}


def logout(token):
    user = models.get_user_by_token(token)
    if user:
        models.clear_user_token(user["id"])


def get_user_by_token(token):
    user = models.get_user_by_token(token)
    if not user:
        return None
    return {"id": user["id"], "username": user["username"], "display_name": user["display_name"]}
```

- [ ] **步骤 5：运行测试验证通过**

运行：`pytest backend/tests/test_auth.py -v`
预期：7 个 PASS。

- [ ] **步骤 6：Commit**

```bash
git add backend/app/services/auth_service.py backend/app/models.py backend/tests/test_auth.py
git commit -m "feat: 认证服务（注册/登录/登出，PBKDF2 哈希）"
```

---

## 任务 2：FastAPI 鉴权依赖

【用户视角】受保护接口需要带 Authorization: Bearer {token}，无 token 或无效 token 返回 401，非成员/非队长返回 403。

**文件：**
- 创建：`backend/app/deps.py`
- 修改：`backend/app/models.py`
- 测试：`backend/tests/test_permissions.py`

- [ ] **步骤 1：在 models.py 加成员相关 CRUD**

在 `backend/app/models.py` 末尾追加：

```python
def add_project_member(project_id, user_id, role):
    with db.get_conn() as conn:
        conn.execute(
            "INSERT INTO project_members(project_id, user_id, role) VALUES(?,?,?)",
            (project_id, user_id, role))


def get_project_member(project_id, user_id):
    with db.get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM project_members WHERE project_id=? AND user_id=?",
            (project_id, user_id)).fetchone()
        return dict(row) if row else None


def list_project_members(project_id):
    with db.get_conn() as conn:
        rows = conn.execute(
            """SELECT pm.role, pm.joined_at, u.id, u.username, u.display_name
               FROM project_members pm JOIN users u ON pm.user_id=u.id
               WHERE pm.project_id=? ORDER BY pm.joined_at""",
            (project_id,)).fetchall()
        return [dict(r) for r in rows]


def list_projects_for_user(user_id):
    with db.get_conn() as conn:
        rows = conn.execute(
            """SELECT p.* FROM projects p
               JOIN project_members pm ON pm.project_id=p.id
               WHERE pm.user_id=? ORDER BY p.id DESC""",
            (user_id,)).fetchall()
        return [dict(r) for r in rows]


def set_project_creator(project_id, user_id):
    with db.get_conn() as conn:
        conn.execute("UPDATE projects SET creator_id=? WHERE id=?", (user_id, project_id))
```

- [ ] **步骤 2：编写失败测试**

创建 `backend/tests/test_permissions.py`：

```python
import pytest
from fastapi import HTTPException
from app.services import auth_service
from app import deps, models


def _make_user_and_token(username="u1"):
    return auth_service.register(username, "pw", username)


def _make_project_with_leader(username="leader"):
    result = auth_service.register(username, "pw", "队长")
    pid = models.create_project("P", "2026-12-31", 3, "desc")
    models.add_project_member(pid, result["user"]["id"], "leader")
    return pid, result["token"], result["user"]["id"]


def test_get_current_user_valid_token():
    r = _make_user_and_token("u_valid")
    user = deps.get_current_user(r["token"])
    assert user["username"] == "u_valid"


def test_get_current_user_invalid_token_raises_401():
    with pytest.raises(HTTPException) as e:
        deps.get_current_user("invalid")
    assert e.value.status_code == 401


def test_require_member_allowed():
    pid, token, uid = _make_project_with_leader("leader_m")
    user = deps.get_current_user(token)
    deps.require_member(pid, user)


def test_require_member_not_in_project_raises_403():
    r = auth_service.register("outsider", "pw", "外人")
    pid, _, _ = _make_project_with_leader("leader_x")
    user = deps.get_current_user(r["token"])
    with pytest.raises(HTTPException) as e:
        deps.require_member(pid, user)
    assert e.value.status_code == 403


def test_require_leader_leader_ok():
    pid, token, _ = _make_project_with_leader("leader_ok")
    user = deps.get_current_user(token)
    deps.require_leader(pid, user)


def test_require_leader_member_raises_403():
    pid, _, _ = _make_project_with_leader("leader_y")
    member = auth_service.register("mem_y", "pw", "队员")
    models.add_project_member(pid, member["user"]["id"], "member")
    user = deps.get_current_user(member["token"])
    with pytest.raises(HTTPException) as e:
        deps.require_leader(pid, user)
    assert e.value.status_code == 403
```

- [ ] **步骤 3：运行测试验证失败**

运行：`pytest backend/tests/test_permissions.py -v`
预期：FAIL，`ModuleNotFoundError: app.deps`。

- [ ] **步骤 4：创建 deps.py**

创建 `backend/app/deps.py`：

```python
from fastapi import HTTPException
from app.services import auth_service


def get_current_user(token: str | None = None) -> dict:
    """token 无效或为空 → 401。"""
    if not token:
        raise HTTPException(status_code=401, detail="未登录")
    user = auth_service.get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="token 无效")
    return user


def require_member(project_id: int, user: dict):
    """非项目成员 → 403。"""
    from app import models
    if not models.get_project_member(project_id, user["id"]):
        raise HTTPException(status_code=403, detail="非项目成员")
    return user


def require_leader(project_id: int, user: dict):
    """非队长 → 403。"""
    from app import models
    member = models.get_project_member(project_id, user["id"])
    if not member:
        raise HTTPException(status_code=403, detail="非项目成员")
    if member["role"] != "leader":
        raise HTTPException(status_code=403, detail="需要队长权限")
    return user
```

- [ ] **步骤 5：运行测试验证通过**

运行：`pytest backend/tests/test_permissions.py -v`
预期：6 个 PASS。

- [ ] **步骤 6：Commit**

```bash
git add backend/app/deps.py backend/app/models.py backend/tests/test_permissions.py
git commit -m "feat: 鉴权依赖（get_current_user/require_member/require_leader）"
```

---

## 任务 3：邀请码与加入

【用户视角】队长能生成 6 位邀请码，队员用码加入项目，码 7 天过期，用过即失效。

**文件：**
- 修改：`backend/app/models.py`
- 创建：`backend/app/services/member_service.py`
- 测试：`backend/tests/test_invite.py`

- [ ] **步骤 1：在 models.py 加邀请码 CRUD**

在 `backend/app/models.py` 末尾追加：

```python
def create_invite(project_id, code, expires_at):
    with db.get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO invite_codes(project_id, code, expires_at) VALUES(?,?,?)",
            (project_id, code, expires_at))
        return cur.lastrowid


def get_invite_by_code(code):
    with db.get_conn() as conn:
        row = conn.execute("SELECT * FROM invite_codes WHERE code=?", (code,)).fetchone()
        return dict(row) if row else None


def mark_invite_used(invite_id, user_id):
    with db.get_conn() as conn:
        conn.execute("UPDATE invite_codes SET used_by_user_id=? WHERE id=?", (user_id, invite_id))
```

- [ ] **步骤 2：编写失败测试**

创建 `backend/tests/test_invite.py`：

```python
import pytest
from datetime import datetime, timedelta
from app.services import auth_service, member_service
from app import models


def _setup_leader_and_project(username="leader"):
    r = auth_service.register(username, "pw", "队长")
    pid = models.create_project("P", "2026-12-31", 3, "desc")
    models.set_project_creator(pid, r["user"]["id"])
    models.add_project_member(pid, r["user"]["id"], "leader")
    return pid, r["user"]["id"], r["token"]


def test_generate_invite_returns_6char_code():
    pid, _, token = _setup_leader_and_project("l1")
    result = member_service.generate_invite(pid, token)
    assert len(result["code"]) == 6
    assert result["code"].isupper()


def test_member_joins_with_valid_code():
    pid, _, leader_token = _setup_leader_and_project("l2")
    inv = member_service.generate_invite(pid, leader_token)
    member = auth_service.register("mem2", "pw", "队员")
    member_service.join_with_code(inv["code"], member["token"])
    m = models.get_project_member(pid, member["user"]["id"])
    assert m["role"] == "member"


def test_used_code_cannot_reuse():
    pid, _, leader_token = _setup_leader_and_project("l3")
    inv = member_service.generate_invite(pid, leader_token)
    m1 = auth_service.register("m3a", "pw", "队员A")
    member_service.join_with_code(inv["code"], m1["token"])
    m2 = auth_service.register("m3b", "pw", "队员B")
    with pytest.raises(ValueError, match="邀请码"):
        member_service.join_with_code(inv["code"], m2["token"])


def test_expired_code_raises():
    pid, _, leader_token = _setup_leader_and_project("l4")
    expires = (datetime.now() - timedelta(days=1)).isoformat()
    models.create_invite(pid, "OLDCOD", expires)
    member = auth_service.register("m4", "pw", "队员")
    with pytest.raises(ValueError, match="过期"):
        member_service.join_with_code("OLDCOD", member["token"])


def test_unknown_code_raises():
    member = auth_service.register("m5", "pw", "队员")
    with pytest.raises(ValueError, match="邀请码"):
        member_service.join_with_code("NOPE00", member["token"])
```

- [ ] **步骤 3：运行测试验证失败**

运行：`pytest backend/tests/test_invite.py -v`
预期：FAIL，`ModuleNotFoundError: app.services.member_service`。

- [ ] **步骤 4：创建 member_service.py**

创建 `backend/app/services/member_service.py`：

```python
import secrets
import string
from datetime import datetime, timedelta
from app import models
from app.services import auth_service


def generate_invite(project_id, leader_token):
    """队长生成 6 位邀请码，7 天有效。权限校验由路由层做。"""
    leader = auth_service.get_user_by_token(leader_token)
    if not leader:
        raise ValueError("无效 token")
    code = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
    expires_at = (datetime.now() + timedelta(days=7)).isoformat()
    models.create_invite(project_id, code, expires_at)
    return {"code": code, "expires_at": expires_at}


def join_with_code(code, member_token):
    """队员用邀请码加入项目。"""
    member = auth_service.get_user_by_token(member_token)
    if not member:
        raise ValueError("无效 token")
    invite = models.get_invite_by_code(code)
    if not invite:
        raise ValueError("邀请码不存在")
    if invite["used_by_user_id"]:
        raise ValueError("邀请码已被使用")
    if datetime.fromisoformat(invite["expires_at"]) < datetime.now():
        raise ValueError("邀请码已过期")
    models.add_project_member(invite["project_id"], member["id"], "member")
    models.mark_invite_used(invite["id"], member["id"])
    return {"project_id": invite["project_id"]}
```

- [ ] **步骤 5：运行测试验证通过**

运行：`pytest backend/tests/test_invite.py -v`
预期：5 个 PASS。

- [ ] **步骤 6：Commit**

```bash
git add backend/app/services/member_service.py backend/app/models.py backend/tests/test_invite.py
git commit -m "feat: 邀请码生成与加入（6 位码、7 天过期、用后失效）"
```

---

## 任务 4：认证路由与项目路由改造

【用户视角】前端能调 /api/auth/register 等接口注册登录，创建项目需登录且自动绑队长，项目列表按用户过滤。

**文件：**
- 创建：`backend/app/routes/auth.py`
- 修改：`backend/app/routes/projects.py`
- 修改：`backend/app/services/project_service.py`
- 修改：`backend/app/main.py`

- [ ] **步骤 1：创建 auth.py 路由**

创建 `backend/app/routes/auth.py`：

```python
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from app.services import auth_service, member_service
from app import deps

router = APIRouter()


class RegisterReq(BaseModel):
    username: str
    password: str
    display_name: str


class LoginReq(BaseModel):
    username: str
    password: str


class JoinReq(BaseModel):
    invite_code: str


def _extract_token(authorization: str | None) -> str | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    return authorization[7:]


@router.post("/api/auth/register")
def register(req: RegisterReq):
    try:
        return auth_service.register(req.username, req.password, req.display_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/auth/login")
def login(req: LoginReq):
    try:
        return auth_service.login(req.username, req.password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/auth/logout")
def logout(authorization: str | None = Header(None)):
    token = _extract_token(authorization)
    if token:
        auth_service.logout(token)
    return {"ok": True}


@router.post("/api/auth/join")
def join(req: JoinReq, authorization: str | None = Header(None)):
    token = _extract_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="未登录")
    try:
        return member_service.join_with_code(req.invite_code, token)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/api/auth/me")
def me(authorization: str | None = Header(None)):
    token = _extract_token(authorization)
    return deps.get_current_user(token)
```

- [ ] **步骤 2：修改 project_service.create_project_with_plan 接收 creator_id**

修改 `backend/app/services/project_service.py` 函数签名与开头：

```python
def create_project_with_plan(name, deadline, team_size, topic_desc, creator_id=None):
    pid = models.create_project(name, deadline, team_size, topic_desc)
    if creator_id:
        models.set_project_creator(pid, creator_id)
        models.add_project_member(pid, creator_id, "leader")

    refs = knowledge_service.match_references(topic_desc)
    kb_context = knowledge_service.build_prompt_context(refs)
    # ...（后续 LLM 调用与任务创建逻辑不变）
```

- [ ] **步骤 3：修改 projects.py 路由加鉴权**

替换 `backend/app/routes/projects.py`：

```python
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from app.services import project_service
from app import models, deps

router = APIRouter()


class ProjectCreate(BaseModel):
    name: str
    deadline: str
    team_size: int
    topic_desc: str


def _extract_token(authorization: str | None) -> str | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    return authorization[7:]


def _current_user(authorization: str | None):
    return deps.get_current_user(_extract_token(authorization))


@router.post("/api/projects")
def create_project(req: ProjectCreate, authorization: str | None = Header(None)):
    user = _current_user(authorization)
    try:
        result = project_service.create_project_with_plan(
            req.name, req.deadline, req.team_size, req.topic_desc, creator_id=user["id"])
        pid = result["project_id"]
        detail = project_service.get_project_detail(pid)
        detail["used_references"] = result["used_references"]
        detail["current_role"] = "leader"
        return {"project_id": pid, "detail": detail}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/projects")
def list_projects(authorization: str | None = Header(None)):
    user = _current_user(authorization)
    return models.list_projects_for_user(user["id"])


@router.get("/api/projects/{pid}")
def get_project(pid: int, authorization: str | None = Header(None)):
    user = _current_user(authorization)
    deps.require_member(pid, user)
    detail = project_service.get_project_detail(pid)
    member = models.get_project_member(pid, user["id"])
    detail["current_role"] = member["role"] if member else None
    return detail
```

- [ ] **步骤 4：在 main.py 注册 auth 路由**

修改 `backend/app/main.py`：

```python
from app.routes import projects, validate, replan, notify, tasks, auth
```

在 `app.include_router(tasks.router)` 后追加 `app.include_router(auth.router)`。

- [ ] **步骤 5：手动冒烟**

运行后端：`uvicorn app.main:app --port 8002`

```powershell
(Invoke-WebRequest -UseBasicParsing -Method GET "http://127.0.0.1:8002/api/projects").StatusCode
```
预期：401（无 token）。

```powershell
$body = '{"username":"test1","password":"pw","display_name":"测试"}'
(Invoke-WebRequest -UseBasicParsing -Method POST "http://127.0.0.1:8002/api/auth/register" -ContentType "application/json" -Body $body).Content
```
预期：返回含 token 的 JSON。

- [ ] **步骤 6：Commit**

```bash
git add backend/app/routes/auth.py backend/app/routes/projects.py backend/app/services/project_service.py backend/app/main.py
git commit -m "feat: 认证路由 + 项目路由鉴权（创建绑队长、列表按用户过滤）"
```

---

## 任务 5：任务审阅服务与状态机

【用户视角】队员能提交任务产物，队长能审阅通过/拒绝，审阅状态独立流转不污染任务状态机。

**文件：**
- 修改：`backend/app/state_machine.py`
- 修改：`backend/app/models.py`
- 创建：`backend/app/services/review_service.py`
- 测试：`backend/tests/test_task_review.py`

- [ ] **步骤 1：扩展 state_machine.py 加 ReviewStatus**

在 `backend/app/state_machine.py` 末尾追加（不改动现有 TaskStatus 流转）：

```python
class ReviewStatus(str, Enum):
    PENDING = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"


def transition_review(current, event: str) -> ReviewStatus:
    """任务审阅状态流转。event: submit | approve | reject | resubmit。"""
    _REVIEW = {
        None: {"submit": ReviewStatus.PENDING},
        ReviewStatus.PENDING: {"approve": ReviewStatus.APPROVED, "reject": ReviewStatus.REJECTED, "resubmit": ReviewStatus.PENDING},
        ReviewStatus.REJECTED: {"resubmit": ReviewStatus.PENDING},
        ReviewStatus.APPROVED: {},
    }
    allowed = _REVIEW.get(current, {})
    if event not in allowed:
        raise InvalidTransition(f"审阅状态 {current} 不允许事件 {event}")
    return allowed[event]
```

- [ ] **步骤 2：在 models.py 加任务审阅字段读写**

在 `backend/app/models.py` 末尾追加：

```python
def assign_task(task_id, assignee_id):
    with db.get_conn() as conn:
        conn.execute("UPDATE tasks SET assignee_id=? WHERE id=?", (assignee_id, task_id))


def submit_task(task_id, submission_filename, submission_path):
    with db.get_conn() as conn:
        conn.execute(
            """UPDATE tasks SET submission_filename=?, submission_path=?,
               review_status='pending_review' WHERE id=?""",
            (submission_filename, submission_path, task_id))


def review_task(task_id, decision, reviewer_id, comment=None):
    """decision: 'approved' | 'rejected'"""
    from datetime import datetime
    conn_status = "approved" if decision == "approved" else "rejected"
    with db.get_conn() as conn:
        conn.execute(
            """UPDATE tasks SET review_status=?, reviewed_by=?, reviewed_at=?, review_comment=?
               WHERE id=?""",
            (conn_status, reviewer_id, datetime.now().isoformat(), comment, task_id))


def insert_notification(project_id, ntype, content, status, scheduled_at):
    """审阅通知用，签名对齐现有 notifications 表。"""
    with db.get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO notifications(project_id, type, content, status, scheduled_at) VALUES(?,?,?,?,?)",
            (project_id, ntype, content, status, scheduled_at))
        return cur.lastrowid
```

注意：`insert_notification` 签名需对齐现有 `notifications` 表实际字段，步骤执行前先 `Read backend/app/models.py` 确认现有 `insert_notification` 是否已存在；若已存在则复用，不重复定义。

- [ ] **步骤 3：编写失败测试**

创建 `backend/tests/test_task_review.py`：

```python
import pytest
from app.services import auth_service, review_service
from app import models


def _setup_project_with_leader_and_member(prefix="r"):
    leader = auth_service.register(f"{prefix}_leader", "pw", "队长")
    member = auth_service.register(f"{prefix}_member", "pw", "队员")
    pid = models.create_project("P", "2026-12-31", 3, "desc")
    models.set_project_creator(pid, leader["user"]["id"])
    models.add_project_member(pid, leader["user"]["id"], "leader")
    models.add_project_member(pid, member["user"]["id"], "member")
    mid = models.create_milestone(pid, "M1", 0, "md")
    tid = models.create_task(mid, pid, "T1", "", "optional", "mid", 1.0, None, None)
    return pid, mid, tid, leader, member


def test_leader_assigns_task_to_member():
    pid, mid, tid, leader, member = _setup_project_with_leader_and_member("a")
    review_service.assign_task(tid, member["user"]["id"], leader["token"], pid)
    task = models.get_task(tid)
    assert task["assignee_id"] == member["user"]["id"]


def test_member_cannot_assign():
    pid, mid, tid, leader, member = _setup_project_with_leader_and_member("b")
    with pytest.raises(PermissionError, match="队长"):
        review_service.assign_task(tid, member["user"]["id"], member["token"], pid)


def test_member_claims_unassigned_task():
    pid, mid, tid, leader, member = _setup_project_with_leader_and_member("c")
    review_service.claim_task(tid, member["token"], pid)
    task = models.get_task(tid)
    assert task["assignee_id"] == member["user"]["id"]


def test_member_submits_and_leader_approves(tmp_path):
    pid, mid, tid, leader, member = _setup_project_with_leader_and_member("d")
    review_service.assign_task(tid, member["user"]["id"], leader["token"], pid)
    f = tmp_path / "demo.md"
    f.write_text("# demo\ncontent")
    review_service.submit_task(tid, "demo.md", str(f), member["token"], pid)
    task = models.get_task(tid)
    assert task["review_status"] == "pending_review"
    review_service.review_task(tid, "approved", leader["token"], pid, "做得好")
    task = models.get_task(tid)
    assert task["review_status"] == "approved"
    assert task["review_comment"] == "做得好"


def test_member_cannot_review():
    pid, mid, tid, leader, member = _setup_project_with_leader_and_member("e")
    review_service.assign_task(tid, member["user"]["id"], leader["token"], pid)
    with pytest.raises(PermissionError, match="队长"):
        review_service.review_task(tid, "approved", member["token"], pid)


def test_non_assignee_cannot_submit(tmp_path):
    pid, mid, tid, leader, member = _setup_project_with_leader_and_member("f")
    review_service.assign_task(tid, member["user"]["id"], leader["token"], pid)
    other = auth_service.register("f_other", "pw", "其他人")
    models.add_project_member(pid, other["user"]["id"], "member")
    f = tmp_path / "x.md"
    f.write_text("x")
    with pytest.raises(PermissionError, match="负责人"):
        review_service.submit_task(tid, "x.md", str(f), other["token"], pid)
```

- [ ] **步骤 4：运行测试验证失败**

运行：`pytest backend/tests/test_task_review.py -v`
预期：FAIL，`ModuleNotFoundError: app.services.review_service`。

- [ ] **步骤 5：创建 review_service.py**

创建 `backend/app/services/review_service.py`：

```python
from app import models, deps
from app.services import auth_service


def _user_from_token(token):
    user = auth_service.get_user_by_token(token)
    if not user:
        raise PermissionError("无效 token")
    return user


def assign_task(task_id, assignee_id, leader_token, project_id):
    leader = _user_from_token(leader_token)
    deps.require_leader(project_id, leader)
    models.assign_task(task_id, assignee_id)


def claim_task(task_id, member_token, project_id):
    member = _user_from_token(member_token)
    deps.require_member(project_id, member)
    task = models.get_task(task_id)
    if not task:
        raise ValueError("任务不存在")
    if task["assignee_id"] is not None:
        raise ValueError("任务已被认领")
    models.assign_task(task_id, member["id"])


def submit_task(task_id, filename, filepath, member_token, project_id):
    member = _user_from_token(member_token)
    deps.require_member(project_id, member)
    task = models.get_task(task_id)
    if not task:
        raise ValueError("任务不存在")
    if task["assignee_id"] != member["id"]:
        raise PermissionError("只有任务负责人能提交")
    models.submit_task(task_id, filename, filepath)
    _notify_leader(project_id, "task_submit",
                   f"{member['display_name']} 提交了任务 {task['title']}，待审阅")


def review_task(task_id, decision, leader_token, project_id, comment=None):
    leader = _user_from_token(leader_token)
    deps.require_leader(project_id, leader)
    task = models.get_task(task_id)
    if not task:
        raise ValueError("任务不存在")
    models.review_task(task_id, decision, leader["id"], comment)
    if task.get("assignee_id"):
        assignee = models.get_user(task["assignee_id"])
        if assignee:
            verb = "已通过" if decision == "approved" else "需修改"
            content = f"任务 {task['title']} {verb}"
            if comment:
                content += f"：{comment}"
            models.insert_notification(project_id, "task_review", content, "sent", None)


def _notify_leader(project_id, ntype, content):
    members = models.list_project_members(project_id)
    for m in members:
        if m["role"] == "leader":
            models.insert_notification(project_id, ntype, content, "sent", None)
            break
```

- [ ] **步骤 6：运行测试验证通过**

运行：`pytest backend/tests/test_task_review.py -v`
预期：6 个 PASS。

- [ ] **步骤 7：Commit**

```bash
git add backend/app/state_machine.py backend/app/models.py backend/app/services/review_service.py backend/tests/test_task_review.py
git commit -m "feat: 任务审阅服务（分配/认领/提交/审阅，权限校验+通知）"
```

---

## 任务 6：审阅与成员路由

【用户视角】前端能调路由完成分配/认领/提交/审阅，能拉成员列表与进度统计。

**文件：**
- 创建：`backend/app/routes/reviews.py`
- 创建：`backend/app/routes/members.py`
- 修改：`backend/app/services/member_service.py`
- 修改：`backend/app/main.py`

- [ ] **步骤 1：在 member_service.py 加进度统计**

在 `backend/app/services/member_service.py` 末尾追加：

```python
def get_member_progress(project_id):
    """返回项目每个成员的进度统计 + 待审阅任务列表。"""
    members = models.list_project_members(project_id)
    tasks = models.list_tasks_by_project(project_id)
    result = []
    for m in members:
        my_tasks = [t for t in tasks if t.get("assignee_id") == m["id"]]
        done = sum(1 for t in my_tasks if t["status"] == "done")
        pending_review = sum(1 for t in my_tasks if t.get("review_status") == "pending_review")
        todo = sum(1 for t in my_tasks if t["status"] in ("planned", "doing"))
        total = len(my_tasks)
        pct = round(done / total * 100) if total else 0
        result.append({
            "user": {"id": m["id"], "username": m["username"], "display_name": m["display_name"]},
            "role": m["role"],
            "total": total, "done": done,
            "pending_review": pending_review, "todo": todo,
            "percent": pct,
            "tasks": my_tasks})
    pending = [t for t in tasks if t.get("review_status") == "pending_review"]
    return {"members": result, "pending_review": pending}
```

- [ ] **步骤 2：创建 reviews.py 路由**

创建 `backend/app/routes/reviews.py`：

```python
from fastapi import APIRouter, HTTPException, Header, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel
from app.services import review_service
from app import deps, models
from pathlib import Path
from datetime import datetime

router = APIRouter()


def _token(authorization: str | None):
    if not authorization or not authorization.startswith("Bearer "):
        return None
    return authorization[7:]


class AssignReq(BaseModel):
    assignee_id: int


class ReviewReq(BaseModel):
    decision: str  # approved | rejected
    comment: str | None = None


def _get_task_or_404(task_id):
    task = models.get_task(task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    return task


@router.post("/api/tasks/{task_id}/assign")
def assign(task_id: int, req: AssignReq, authorization: str | None = Header(None)):
    token = _token(authorization)
    user = deps.get_current_user(token)
    task = _get_task_or_404(task_id)
    deps.require_leader(task["project_id"], user)
    review_service.assign_task(task_id, req.assignee_id, token, task["project_id"])
    return {"ok": True}


@router.post("/api/tasks/{task_id}/claim")
def claim(task_id: int, authorization: str | None = Header(None)):
    token = _token(authorization)
    user = deps.get_current_user(token)
    task = _get_task_or_404(task_id)
    deps.require_member(task["project_id"], user)
    try:
        review_service.claim_task(task_id, token, task["project_id"])
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True}


@router.post("/api/tasks/{task_id}/submit")
async def submit(task_id: int, file: UploadFile = File(...), authorization: str | None = Header(None)):
    token = _token(authorization)
    user = deps.get_current_user(token)
    task = _get_task_or_404(task_id)
    deps.require_member(task["project_id"], user)
    upload_dir = Path("data/submissions")
    upload_dir.mkdir(parents=True, exist_ok=True)
    save_name = f"{task_id}_{int(datetime.now().timestamp())}_{file.filename}"
    save_path = upload_dir / save_name
    save_path.write_bytes(await file.read())
    review_service.submit_task(task_id, file.filename, str(save_path), token, task["project_id"])
    return {"ok": True, "filename": file.filename}


@router.post("/api/tasks/{task_id}/review")
def review(task_id: int, req: ReviewReq, authorization: str | None = Header(None)):
    token = _token(authorization)
    user = deps.get_current_user(token)
    task = _get_task_or_404(task_id)
    deps.require_leader(task["project_id"], user)
    review_service.review_task(task_id, req.decision, token, task["project_id"], req.comment)
    return {"ok": True}


@router.get("/api/tasks/{task_id}/submission")
def download_submission(task_id: int, authorization: str | None = Header(None)):
    token = _token(authorization)
    user = deps.get_current_user(token)
    task = _get_task_or_404(task_id)
    deps.require_member(task["project_id"], user)
    if not task.get("submission_path"):
        raise HTTPException(404, "无提交产物")
    pm = models.get_project_member(task["project_id"], user["id"])
    if pm["role"] != "leader" and task["assignee_id"] != user["id"]:
        raise HTTPException(403, "无权下载")
    return FileResponse(task["submission_path"], filename=task["submission_filename"])
```

- [ ] **步骤 3：创建 members.py 路由**

创建 `backend/app/routes/members.py`：

```python
from fastapi import APIRouter, Header
from app.services import member_service
from app import models, deps

router = APIRouter()


def _token(authorization: str | None):
    if not authorization or not authorization.startswith("Bearer "):
        return None
    return authorization[7:]


@router.post("/api/projects/{pid}/invites")
def create_invite(pid: int, authorization: str | None = Header(None)):
    token = _token(authorization)
    user = deps.get_current_user(token)
    deps.require_leader(pid, user)
    return member_service.generate_invite(pid, token)


@router.get("/api/projects/{pid}/members")
def list_members(pid: int, authorization: str | None = Header(None)):
    token = _token(authorization)
    user = deps.get_current_user(token)
    deps.require_member(pid, user)
    return models.list_project_members(pid)


@router.get("/api/projects/{pid}/progress")
def get_progress(pid: int, authorization: str | None = Header(None)):
    token = _token(authorization)
    user = deps.get_current_user(token)
    deps.require_member(pid, user)
    progress = member_service.get_member_progress(pid)
    member = models.get_project_member(pid, user["id"])
    if member and member["role"] != "leader":
        progress["members"] = [m for m in progress["members"] if m["user"]["id"] == user["id"]]
        progress["pending_review"] = []
    return progress
```

- [ ] **步骤 4：在 main.py 注册新路由**

修改 `backend/app/main.py`：

```python
from app.routes import projects, validate, replan, notify, tasks, auth, reviews, members
```

追加：

```python
app.include_router(reviews.router)
app.include_router(members.router)
```

- [ ] **步骤 5：运行全部测试**

运行：`pytest backend/tests/ -v`
预期：全部 PASS。

- [ ] **步骤 6：Commit**

```bash
git add backend/app/routes/reviews.py backend/app/routes/members.py backend/app/services/member_service.py backend/app/main.py
git commit -m "feat: 审阅与成员路由（分配/认领/提交/审阅/进度，权限校验）"
```

---

## 任务 7：tasks 路由鉴权改造

【用户视角】改任务状态需要是任务负责人或队长，外人无法改。

**文件：**
- 修改：`backend/app/routes/tasks.py`

- [ ] **步骤 1：修改 tasks.py 加权限校验**

替换 `backend/app/routes/tasks.py`：

```python
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from app import models, deps
from app.state_machine import TaskStatus, transition_task, InvalidTransition
from datetime import datetime

router = APIRouter()


class CheckinReq(BaseModel):
    note: str = ""


class StatusUpdate(BaseModel):
    event: str  # start | complete | overdue


def _token(authorization: str | None):
    if not authorization or not authorization.startswith("Bearer "):
        return None
    return authorization[7:]


@router.post("/api/tasks/{task_id}/checkin")
def checkin(task_id: int, req: CheckinReq, authorization: str | None = Header(None)):
    token = _token(authorization)
    user = deps.get_current_user(token)
    task = models.get_task(task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    deps.require_member(task["project_id"], user)
    models.insert_checkin(task_id, req.note)
    return {"ok": True}


@router.patch("/api/tasks/{task_id}/status")
def update_status(task_id: int, req: StatusUpdate, authorization: str | None = Header(None)):
    token = _token(authorization)
    user = deps.get_current_user(token)
    task = models.get_task(task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    deps.require_member(task["project_id"], user)
    member = models.get_project_member(task["project_id"], user["id"])
    if member["role"] != "leader" and task.get("assignee_id") != user["id"]:
        raise HTTPException(403, "只有任务负责人或队长可改状态")
    try:
        new_status = transition_task(TaskStatus(task["status"]), req.event)
    except InvalidTransition as e:
        raise HTTPException(400, str(e))
    completed_at = datetime.now().isoformat() if new_status == TaskStatus.DONE else None
    models.update_task_status(task_id, new_status.value, completed_at)
    return {"task_id": task_id, "status": new_status.value}
```

- [ ] **步骤 2：运行全部测试确认未破坏**

运行：`pytest backend/tests/ -v`
预期：全部 PASS。

- [ ] **步骤 3：Commit**

```bash
git add backend/app/routes/tasks.py
git commit -m "feat: 任务状态变更加权限校验（负责人或队长）"
```

---

## 任务 8：前端 hash 路由与鉴权状态

【用户视角】前端能根据登录状态跳转登录页或项目列表页，刷新不丢项目，所有请求自动带 token。

**文件：**
- 修改：`frontend/static/app.js`
- 修改：`frontend/index.html`

- [ ] **步骤 1：重写 app.js 加路由与鉴权**

替换 `frontend/static/app.js`：

```javascript
function app() {
  return {
    view: 'login',
    currentUser: null,
    token: localStorage.getItem('cc_token') || null,
    project: null, milestones: [], tasks: [], notifications: [],
    usedReferences: null, currentRole: null,

    init() {
      if (this.token) {
        this.fetchUser();
      } else {
        this.navigate('login');
      }
      window.addEventListener('hashchange', () => this.handleHash());
      this.handleHash();
    },

    handleHash() {
      const h = location.hash.slice(1);
      if (!this.token) { this.view = 'login'; return; }
      if (h.startsWith('/projects/new')) this.view = 'create';
      else if (h.startsWith('/projects/') && h.endsWith('/members')) {
        const pid = h.match(/\/projects\/(\d+)/)?.[1];
        if (pid) { this.loadProject(pid); this.view = 'members'; }
      } else if (h.startsWith('/projects/')) {
        const pid = h.match(/\/projects\/(\d+)/)?.[1];
        if (pid) this.loadProject(pid);
      } else {
        this.view = 'projects';
      }
    },

    navigate(path) {
      location.hash = path;
      this.handleHash();
    },

    async fetchUser() {
      try {
        const r = await fetch('/api/auth/me', { headers: this.authHeaders() });
        if (r.ok) {
          this.currentUser = await r.json();
        } else {
          this.logout();
        }
      } catch { this.logout(); }
    },

    authHeaders() {
      return this.token ? { 'Authorization': 'Bearer ' + this.token } : {};
    },

    setToken(token) {
      this.token = token;
      localStorage.setItem('cc_token', token);
    },

    logout() {
      fetch('/api/auth/logout', { method: 'POST', headers: this.authHeaders() });
      this.token = null;
      this.currentUser = null;
      localStorage.removeItem('cc_token');
      this.navigate('login');
    },

    async createProject(form) {
      const r = await fetch('/api/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...this.authHeaders() },
        body: JSON.stringify(form)
      });
      if (!r.ok) throw new Error(await r.text());
      const data = await r.json();
      this.navigate('/projects/' + data.project_id);
    },

    async loadProject(pid) {
      const r = await fetch(`/api/projects/${pid}`, { headers: this.authHeaders() });
      if (!r.ok) { this.navigate('projects'); return; }
      const data = await r.json();
      this.project = data.project;
      this.milestones = data.milestones;
      this.tasks = data.tasks;
      this.usedReferences = data.used_references || null;
      this.currentRole = data.current_role;
      this.view = 'board';
    },

    async updateTaskStatus(taskId, event) {
      await fetch(`/api/tasks/${taskId}/status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', ...this.authHeaders() },
        body: JSON.stringify({ event })
      });
      await this.loadProject(this.project.id);
    },

    // —— 罗盘仪表辅助方法（保留现有） ——
    needleAngle() {
      if (!this.milestones.length) return 0;
      const done = this.milestones.filter(m => m.status === 'done').length;
      return Math.round((done / this.milestones.length) * 360);
    },
    currentHeading() {
      if (!this.milestones.length) return '待启航';
      const current = this.milestones.find(m => m.status !== 'done') || this.milestones[0];
      const idx = this.milestones.indexOf(current) + 1;
      return `M${String(idx).padStart(2, '0')} · ${current.name}`;
    },
    progressText() {
      if (!this.milestones.length) return '';
      const done = this.milestones.filter(m => m.status === 'done').length;
      return `${done} / ${this.milestones.length} 里程碑`;
    },
    coordsLabel() {
      if (!this.project) return '— · —';
      const days = Math.max(0, Math.ceil((new Date(this.project.deadline) - new Date()) / 86400000));
      return `${days}d 到岸 · ${this.project.team_size}p`;
    },
    formatDate(s) { return s ? s.slice(0, 10) : ''; },
    formatTime(s) { return s ? s.replace('T', ' ').slice(0, 16) : ''; }
  }
}
```

注意：现有 `triggerOverdue`、`refresh`、`scrollTo` 等方法按 `frontend/static/app.js` 实际保留，本步骤只展示新增/变更的核心方法。执行前先 Read 现有 app.js，把上述方法合并进去而非整体替换。

- [ ] **步骤 2：修改 index.html 根元素加 init**

修改 `frontend/index.html` 的 `<div class="app-shell" x-data="app()">` 为：

```html
<div class="app-shell" x-data="app()" x-init="init()">
```

- [ ] **步骤 3：手动冒烟**

启动后端，访问 `http://127.0.0.1:8002/`，预期看到登录页（view='login'，因无 token）。浏览器控制台无 JS 报错。

- [ ] **步骤 4：Commit**

```bash
git add frontend/static/app.js frontend/index.html
git commit -m "feat: 前端 hash 路由 + 鉴权状态 + token 拦截器"
```

---

## 任务 9：登录页与项目列表页

【用户视角】能在登录页注册/登录，登录后看到自己的项目列表，队长能新建项目，队员能输邀请码加入。

**文件：**
- 创建：`frontend/static/components/auth.js`
- 创建：`frontend/static/components/project-list.js`
- 修改：`frontend/index.html`
- 修改：`frontend/static/style.css`

- [ ] **步骤 1：创建 auth.js 组件**

创建 `frontend/static/components/auth.js`：

```javascript
function authView(parent) {
  return {
    mode: 'login',
    form: { username: '', password: '', display_name: '' },
    inviteCode: '',
    error: null,
    loading: false,

    async submit() {
      this.loading = true;
      this.error = null;
      try {
        const url = this.mode === 'login' ? '/api/auth/login' : '/api/auth/register';
        const body = this.mode === 'login'
          ? { username: this.form.username, password: this.form.password }
          : this.form;
        const r = await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body)
        });
        if (!r.ok) {
          const e = await r.json();
          throw new Error(e.detail || '操作失败');
        }
        const data = await r.json();
        parent.setToken(data.token);
        await parent.fetchUser();
        parent.navigate('projects');
      } catch (e) {
        this.error = e.message;
      } finally {
        this.loading = false;
      }
    },

    async join() {
      if (!this.inviteCode) return;
      this.loading = true;
      this.error = null;
      try {
        const r = await fetch('/api/auth/join', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', ...parent.authHeaders() },
          body: JSON.stringify({ invite_code: this.inviteCode })
        });
        if (!r.ok) throw new Error((await r.json()).detail || '加入失败');
        parent.navigate('projects');
      } catch (e) {
        this.error = e.message;
      } finally {
        this.loading = false;
      }
    }
  }
}
```

- [ ] **步骤 2：创建 project-list.js 组件**

创建 `frontend/static/components/project-list.js`：

```javascript
function projectList(parent) {
  return {
    projects: [],
    loading: true,

    async init() {
      await this.load();
    },

    async load() {
      this.loading = true;
      try {
        const r = await fetch('/api/projects', { headers: parent.authHeaders() });
        if (!r.ok) { parent.logout(); return; }
        this.projects = await r.json();
      } finally {
        this.loading = false;
      }
    },

    roleLabel(p) {
      return p.creator_id === parent.currentUser?.id ? '队长' : '队员';
    },
    progressSummary(p) {
      return `${p.team_size} 人团队`;
    }
  }
}
```

- [ ] **步骤 3：在 index.html 加 login 与 projects 视图模板**

在 `frontend/index.html` 的 `<main class="canvas">` 内，现有创建项目视图前插入：

```html
      <!-- 登录视图 -->
      <template x-if="view === 'login'">
        <section class="auth-view" x-data="authView($data)">
          <div class="auth-card">
            <span class="eyebrow">AUTH · 01</span>
            <h1>启航前请登记</h1>
            <div class="auth-tabs">
              <button :class="{active: mode==='login'}" @click="mode='login'">登录</button>
              <button :class="{active: mode==='register'}" @click="mode='register'">注册</button>
            </div>
            <form @submit.prevent="submit()">
              <label class="field">
                <span>用户名</span>
                <input x-model="form.username" required>
              </label>
              <label class="field">
                <span>密码</span>
                <input type="password" x-model="form.password" required>
              </label>
              <label class="field" x-show="mode==='register'" x-cloak>
                <span>显示名</span>
                <input x-model="form.display_name" :required="mode==='register'">
              </label>
              <p class="auth-error" x-show="error" x-text="error" x-cloak></p>
              <button class="btn-primary" :disabled="loading">
                <span x-text="loading ? '处理中…' : (mode==='login' ? '登录' : '注册')"></span>
              </button>
            </form>
            <div class="auth-join">
              <span class="kb-label">队员？输入队长给的邀请码</span>
              <div class="join-row">
                <input x-model="inviteCode" placeholder="6 位邀请码" maxlength="6">
                <button class="btn-ghost" @click="join()" :disabled="loading || !inviteCode">加入</button>
              </div>
            </div>
          </div>
        </section>
      </template>

      <!-- 项目列表视图 -->
      <template x-if="view === 'projects'">
        <section class="projects-view" x-data="projectList($data)" x-init="init()">
          <header class="board-header">
            <div class="title-block">
              <span class="eyebrow">CHART · MY PROJECTS</span>
              <h1>我的航行</h1>
            </div>
            <div class="header-actions">
              <button class="btn-accent" @click="$root.navigate('/projects/new')">+ 启动新航行</button>
            </div>
          </header>
          <div class="project-grid">
            <template x-for="(p, idx) in projects" :key="p.id">
              <article class="project-card" @click="$root.navigate('/projects/' + p.id)">
                <div class="ms-index" x-text="String(idx + 1).padStart(2, '0')"></div>
                <div class="pc-body">
                  <h3 x-text="p.name"></h3>
                  <span class="pc-meta" x-text="progressSummary(p)"></span>
                </div>
                <span class="pc-role" x-text="roleLabel(p)"></span>
              </article>
            </template>
            <p class="empty-state" x-show="!projects.length && !loading">还没有项目。启动一次新航行吧。</p>
          </div>
        </section>
      </template>
```

- [ ] **步骤 4：在 index.html 末尾加新组件 script**

在现有组件 script 标签后追加：

```html
  <script src="/static/components/auth.js"></script>
  <script src="/static/components/project-list.js"></script>
```

- [ ] **步骤 5：在 style.css 加登录页与项目列表样式**

在 `frontend/static/style.css` 末尾追加：

```css
/* ============ 登录页 ============ */
.auth-view {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 70vh;
  padding: 40px 0;
}
.auth-card {
  background: var(--graph);
  border: 1px solid var(--line);
  border-radius: var(--radius-lg);
  padding: 36px 40px;
  width: 100%;
  max-width: 420px;
  position: relative;
  overflow: hidden;
}
.auth-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 60px;
  height: 60px;
  background:
    linear-gradient(var(--compass), var(--compass)) top left / 60px 2px no-repeat,
    linear-gradient(var(--compass), var(--compass)) top left / 2px 60px no-repeat;
}
.auth-card h1 { font-size: 28px; margin-bottom: 22px; }
.auth-tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 20px;
  border-bottom: 1px solid var(--line);
}
.auth-tabs button {
  background: none;
  color: var(--parchment-dim);
  padding: 8px 16px;
  font-size: 13px;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
}
.auth-tabs button.active {
  color: var(--compass);
  border-bottom-color: var(--compass);
}
.auth-error { color: var(--fail); font-size: 12px; margin: 0 0 10px; }
.auth-join {
  margin-top: 22px;
  padding-top: 18px;
  border-top: 1px dashed var(--line);
}
.join-row { display: flex; gap: 8px; margin-top: 8px; }
.join-row input { text-transform: uppercase; letter-spacing: 0.2em; }

/* ============ 项目列表 ============ */
.projects-view { display: flex; flex-direction: column; gap: 24px; }
.project-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}
.project-card {
  background: var(--graph);
  border: 1px solid var(--line);
  border-radius: var(--radius-lg);
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 14px;
  cursor: pointer;
  transition: transform 0.2s, border-color 0.2s;
  position: relative;
}
.project-card:hover {
  transform: translateY(-2px);
  border-color: var(--compass);
}
.pc-body { flex: 1; }
.pc-body h3 { font-size: 16px; margin-bottom: 4px; }
.pc-meta { font-size: 12px; color: var(--parchment-dim); }
.pc-role {
  font-size: 11px;
  color: var(--brass);
  border: 1px solid var(--brass);
  padding: 2px 8px;
  border-radius: 10px;
}
.empty-state { color: var(--parchment-dim); padding: 40px 0; text-align: center; }
```

注意：CSS 变量名（`--graph`、`--line`、`--compass`、`--parchment-dim`、`--brass`、`--radius-lg`、`--fail`）需对齐 `frontend/static/style.css` 现有定义。执行前先 Grep 确认变量名，若不同则改用现有变量。

- [ ] **步骤 6：手动冒烟**

启动后端，浏览器访问 `/`，注册一个用户，预期跳转到项目列表页（空状态"还没有项目"）。

- [ ] **步骤 7：Commit**

```bash
git add frontend/static/components/auth.js frontend/static/components/project-list.js frontend/index.html frontend/static/style.css
git commit -m "feat: 登录页与项目列表页（注册/登录/邀请码加入）"
```

---

## 任务 10：任务看板适配（认领/分配/审阅状态显示）

【用户视角】看板任务行显示负责人与审阅状态，队长能分配，队员能认领，队员能提交产物。

**文件：**
- 创建：`frontend/static/components/task-assign.js`
- 修改：`frontend/static/components/task-board.js`
- 修改：`frontend/index.html`
- 修改：`frontend/static/style.css`

- [ ] **步骤 1：创建 task-assign.js 组件**

创建 `frontend/static/components/task-assign.js`：

```javascript
function taskAssign(parent, task) {
  return {
    showAssignPicker: false,
    reviewComment: '',
    submitting: false,

    async assignTo(userId) {
      const r = await fetch(`/api/tasks/${task.id}/assign`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...parent.authHeaders() },
        body: JSON.stringify({ assignee_id: userId })
      });
      if (!r.ok) { alert('分配失败'); return; }
      this.showAssignPicker = false;
      await parent.loadProject(parent.project.id);
    },

    async claim() {
      const r = await fetch(`/api/tasks/${task.id}/claim`, {
        method: 'POST',
        headers: parent.authHeaders()
      });
      if (!r.ok) { alert((await r.json()).detail || '认领失败'); return; }
      await parent.loadProject(parent.project.id);
    },

    async submitFile(fileInput) {
      const file = fileInput.files[0];
      if (!file) return;
      this.submitting = true;
      try {
        const fd = new FormData();
        fd.append('file', file);
        const r = await fetch(`/api/tasks/${task.id}/submit`, {
          method: 'POST',
          headers: parent.authHeaders(),
          body: fd
        });
        if (!r.ok) { alert((await r.json()).detail || '提交失败'); return; }
        await parent.loadProject(parent.project.id);
      } finally {
        this.submitting = false;
      }
    },

    async review(decision) {
      const r = await fetch(`/api/tasks/${task.id}/review`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...parent.authHeaders() },
        body: JSON.stringify({ decision, comment: this.reviewComment })
      });
      if (!r.ok) { alert('审阅失败'); return; }
      this.reviewComment = '';
      await parent.loadProject(parent.project.id);
    },

    downloadUrl() {
      return `/api/tasks/${task.id}/submission`;
    },

    reviewStatusLabel(status) {
      return {
        pending_review: '待审阅',
        approved: '已通过',
        rejected: '需修改'
      }[status] || '';
    },
    reviewStatusClass(status) {
      return {
        pending_review: 'rv-pending',
        approved: 'rv-approved',
        rejected: 'rv-rejected'
      }[status] || '';
    }
  }
}
```

- [ ] **步骤 2：修改 task-board.js 渲染 assignee + review_status**

先 Read `frontend/static/components/task-board.js` 了解现有任务行渲染。在任务行模板里追加（具体插入位置按现有结构定）：

```javascript
// 在任务行末尾追加（Alpine 模板片段，加到现有 task-item 内）
`
<div class="task-assignee" x-data="taskAssign($root, t)">
  <template x-if="!t.assignee_id && $root.currentRole === 'leader'">
    <div>
      <button class="btn-mini" @click="showAssignPicker = !showAssignPicker">分配</button>
      <div x-show="showAssignPicker" x-cloak>
        <template x-for="m in $root.members" :key="m.id">
          <button @click="assignTo(m.id)" x-text="m.display_name"></button>
        </template>
      </div>
    </div>
  </template>
  <template x-if="!t.assignee_id && $root.currentRole === 'member'">
    <button class="btn-mini" @click="claim()">认领</button>
  </template>
  <template x-if="t.assignee_id">
    <span class="assignee-tag">
      @<span x-text="t.assignee_name || '队员'"></span>
      <template x-if="t.review_status">
        <em :class="reviewStatusClass(t.review_status)" x-text="reviewStatusLabel(t.review_status)"></em>
      </template>
      <template x-if="$root.currentRole !== 'leader' && t.assignee_id === $root.currentUser?.id && t.review_status !== 'approved'">
        <label class="submit-btn">
          提交产物
          <input type="file" @change="submitFile($event.target)" :disabled="submitting" hidden>
        </label>
      </template>
      <template x-if="t.review_status === 'pending_review' && $root.currentRole === 'leader'">
        <span class="review-actions">
          <a :href="downloadUrl()" target="_blank">查看产物</a>
          <button @click="review('approved')">通过</button>
          <button @click="review('rejected')">拒绝</button>
        </span>
      </template>
      <template x-if="t.review_status === 'rejected' && t.review_comment">
        <span class="review-comment" x-text="'意见：' + t.review_comment"></span>
      </template>
    </span>
  </template>
</div>
`
```

注意：`$root.members` 需在 board 视图加载时拉取成员列表，在 app.js 的 `loadProject` 里追加：

```javascript
const mr = await fetch(`/api/projects/${pid}/members`, { headers: this.authHeaders() });
this.members = mr.ok ? await mr.json() : [];
```

且 `app` 返回对象加 `members: []` 初始值。

- [ ] **步骤 3：在 index.html 加载 task-assign.js**

在现有组件 script 后追加：

```html
  <script src="/static/components/task-assign.js"></script>
```

- [ ] **步骤 4：在 style.css 加任务认领/审阅样式**

在 `frontend/static/style.css` 末尾追加：

```css
/* ============ 任务认领与审阅 ============ */
.task-assignee {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px dashed var(--line);
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.assignee-tag {
  color: var(--brass);
}
.assignee-tag em {
  font-style: normal;
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 8px;
  margin-left: 4px;
}
.rv-pending { color: var(--compass); border: 1px solid var(--compass); }
.rv-approved { color: var(--pass, #6abf69); border: 1px solid var(--pass, #6abf69); }
.rv-rejected { color: var(--fail); border: 1px solid var(--fail); }
.btn-mini {
  font-size: 11px;
  padding: 2px 8px;
  background: transparent;
  border: 1px solid var(--brass);
  color: var(--brass);
  border-radius: 4px;
  cursor: pointer;
}
.submit-btn {
  cursor: pointer;
  color: var(--compass);
  text-decoration: underline;
}
.review-actions { display: inline-flex; gap: 6px; align-items: center; }
.review-actions a { color: var(--brass); font-size: 11px; }
.review-actions button {
  font-size: 11px;
  padding: 1px 6px;
  border: 1px solid var(--brass);
  background: transparent;
  color: var(--parchment);
  cursor: pointer;
  border-radius: 3px;
}
.review-comment {
  display: block;
  width: 100%;
  margin-top: 4px;
  color: var(--fail);
  font-size: 11px;
}
```

- [ ] **步骤 5：手动冒烟**

启动后端，注册队长创建项目 → 注册队员用邀请码加入 → 队长分配任务 → 队员认领另一未分配任务 → 队员提交文件 → 队长审阅通过/拒绝。全流程跑通。

- [ ] **步骤 6：Commit**

```bash
git add frontend/static/components/task-assign.js frontend/static/components/task-board.js frontend/index.html frontend/static/style.css frontend/static/app.js
git commit -m "feat: 任务看板认领/分配/提交/审阅 UI"
```

---

## 任务 11：成员进度视图

【用户视角】队长能看到全队每个成员的完成率与待审阅任务，队员只看自己的进度。

**文件：**
- 创建：`frontend/static/components/member-progress.js`
- 修改：`frontend/index.html`
- 修改：`frontend/static/style.css`

- [ ] **步骤 1：创建 member-progress.js 组件**

创建 `frontend/static/components/member-progress.js`：

```javascript
function memberProgress(parent) {
  return {
    data: { members: [], pending_review: [] },
    loading: true,
    reviewComment: '',

    async init() {
      await this.load();
    },

    async load() {
      if (!parent.project) return;
      this.loading = true;
      try {
        const r = await fetch(`/api/projects/${parent.project.id}/progress`, {
          headers: parent.authHeaders()
        });
        if (!r.ok) return;
        this.data = await r.json();
      } finally {
        this.loading = false;
      }
    },

    async review(taskId, decision) {
      const r = await fetch(`/api/tasks/${taskId}/review`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...parent.authHeaders() },
        body: JSON.stringify({ decision, comment: this.reviewComment })
      });
      if (!r.ok) { alert('审阅失败'); return; }
      this.reviewComment = '';
      await this.load();
    },

    downloadUrl(taskId) {
      return `/api/tasks/${taskId}/submission`;
    }
  }
}
```

- [ ] **步骤 2：在 index.html 加 members 视图模板**

在 `frontend/index.html` 的项目列表视图后插入：

```html
      <!-- 成员进度视图 -->
      <template x-if="view === 'members'">
        <section class="members-view" x-data="memberProgress($data)" x-init="init()">
          <header class="board-header">
            <div class="title-block">
              <span class="eyebrow">CREW · PROGRESS</span>
              <h1>成员进度</h1>
            </div>
            <button class="btn-ghost" @click="$root.navigate('/projects/' + $root.project.id)">← 回看板</button>
          </header>

          <!-- 待我审阅（仅队长） -->
          <template x-if="$root.currentRole === 'leader' && data.pending_review.length">
            <div class="review-queue">
              <h2>待我审阅（<span x-text="data.pending_review.length"></span>）</h2>
              <template x-for="t in data.pending_review" :key="t.id">
                <div class="review-item">
                  <div class="ri-head">
                    <strong x-text="t.title"></strong>
                    <span class="ri-time" x-text="$root.formatTime(t.submission_path ? t.id : t.id)"></span>
                  </div>
                  <input class="ri-comment" x-model="reviewComment" placeholder="审阅意见（可选）">
                  <div class="ri-actions">
                    <a :href="downloadUrl(t.id)" target="_blank">查看产物</a>
                    <button class="btn-approve" @click="review(t.id, 'approved')">通过</button>
                    <button class="btn-reject" @click="review(t.id, 'rejected')">拒绝</button>
                  </div>
                </div>
              </template>
            </div>
          </template>

          <!-- 成员列表 -->
          <div class="member-grid">
            <template x-for="m in data.members" :key="m.user.id">
              <article class="member-card">
                <div class="mc-head">
                  <span class="mc-avatar" x-text="m.user.display_name.charAt(0)"></span>
                  <div>
                    <h3 x-text="m.user.display_name"></h3>
                    <span class="mc-role" x-text="m.role === 'leader' ? '队长' : '队员'"></span>
                  </div>
                </div>
                <div class="mc-stats">
                  <span>负责 <strong x-text="m.total"></strong></span>
                  <span>完成 <strong x-text="m.done"></strong></span>
                  <span>审阅中 <strong x-text="m.pending_review"></strong></span>
                  <span>待办 <strong x-text="m.todo"></strong></span>
                </div>
                <div class="mc-bar">
                  <div class="mc-bar-fill" :style="`width: ${m.percent}%`"></div>
                </div>
                <span class="mc-pct" x-text="m.percent + '%'"></span>
              </article>
            </template>
          </div>
        </section>
      </template>
```

- [ ] **步骤 3：在 index.html 加载 member-progress.js**

在现有组件 script 后追加：

```html
  <script src="/static/components/member-progress.js"></script>
```

- [ ] **步骤 4：在 style.css 加成员进度样式**

在 `frontend/static/style.css` 末尾追加：

```css
/* ============ 成员进度视图 ============ */
.members-view { display: flex; flex-direction: column; gap: 24px; }
.review-queue {
  background: var(--graph);
  border: 1px solid var(--compass);
  border-radius: var(--radius-lg);
  padding: 20px;
}
.review-queue h2 { font-size: 16px; color: var(--compass); margin-bottom: 12px; }
.review-item {
  border-top: 1px dashed var(--line);
  padding: 12px 0;
}
.ri-head { display: flex; justify-content: space-between; margin-bottom: 8px; }
.ri-time { font-size: 11px; color: var(--parchment-dim); }
.ri-comment {
  width: 100%;
  background: transparent;
  border: 1px solid var(--line);
  color: var(--parchment);
  padding: 4px 8px;
  margin-bottom: 8px;
  border-radius: 4px;
  font-size: 12px;
}
.ri-actions { display: flex; gap: 10px; align-items: center; }
.ri-actions a { color: var(--brass); font-size: 12px; }
.btn-approve {
  border: 1px solid var(--pass, #6abf69);
  color: var(--pass, #6abf69);
  background: transparent;
  padding: 2px 10px;
  border-radius: 3px;
  cursor: pointer;
  font-size: 12px;
}
.btn-reject {
  border: 1px solid var(--fail);
  color: var(--fail);
  background: transparent;
  padding: 2px 10px;
  border-radius: 3px;
  cursor: pointer;
  font-size: 12px;
}

.member-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}
.member-card {
  background: var(--graph);
  border: 1px solid var(--line);
  border-radius: var(--radius-lg);
  padding: 18px;
}
.mc-head { display: flex; align-items: center; gap: 10px; margin-bottom: 14px; }
.mc-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--brass);
  color: var(--graph);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
}
.mc-head h3 { font-size: 14px; }
.mc-role { font-size: 11px; color: var(--brass); }
.mc-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  font-size: 11px;
  color: var(--parchment-dim);
  margin-bottom: 10px;
}
.mc-stats strong { color: var(--parchment); display: block; font-size: 16px; }
.mc-bar {
  height: 6px;
  background: rgba(201, 169, 97, 0.1);
  border-radius: 3px;
  overflow: hidden;
}
.mc-bar-fill {
  height: 100%;
  background: var(--compass);
  transition: width 0.4s;
}
.mc-pct {
  display: block;
  text-align: right;
  font-size: 11px;
  color: var(--brass);
  margin-top: 4px;
}

@media (max-width: 640px) {
  .member-grid { grid-template-columns: 1fr; }
  .review-queue { order: -1; }
}
```

- [ ] **步骤 5：在罗盘栏加成员进度入口**

在 `frontend/index.html` 罗盘栏导航项里，"通知日志"项前插入（仅 board 视图下显示）：

```html
<template x-if="view === 'board' || view === 'members'">
  <button class="nav-item" @click="navigate('/projects/' + project.id + '/members')">成员进度</button>
</template>
```

- [ ] **步骤 6：手动冒烟**

启动后端，登录队长账号，进入某项目，点"成员进度"，预期看到成员卡片 + 待审阅队列（若有提交）。登录队员账号，预期只看到自己的卡片，无审阅队列。

- [ ] **步骤 7：Commit**

```bash
git add frontend/static/components/member-progress.js frontend/index.html frontend/static/style.css
git commit -m "feat: 成员进度视图（队长看全队+审阅队列，队员看自己）"
```

---

## 任务 12：罗盘栏适配与通知集成

【用户视角】罗盘栏根据登录状态显示用户名/角色/登出，通知日志显示审阅相关通知。

**文件：**
- 修改：`frontend/index.html`
- 修改：`frontend/static/components/notify-log.js`

- [ ] **步骤 1：修改罗盘栏底部显示用户信息**

在 `frontend/index.html` 罗盘栏底部区域（原 `coordsLabel` 显示处），改为：

```html
<template x-if="currentUser">
  <div class="compass-user">
    <span class="cu-name" x-text="currentUser.display_name"></span>
    <span class="cu-role" x-text="currentRole === 'leader' ? '队长' : '队员'"></span>
    <button class="cu-logout" @click="logout()">登出</button>
  </div>
</template>
<template x-if="!currentUser">
  <span class="compass-guest">未登录</span>
</template>
```

- [ ] **步骤 2：在 style.css 加罗盘栏用户样式**

在 `frontend/static/style.css` 末尾追加：

```css
.compass-user {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
}
.cu-name { color: var(--parchment); }
.cu-role {
  color: var(--brass);
  border: 1px solid var(--brass);
  padding: 1px 6px;
  border-radius: 8px;
  font-size: 10px;
}
.cu-logout {
  background: none;
  border: none;
  color: var(--parchment-dim);
  cursor: pointer;
  font-size: 11px;
  text-decoration: underline;
}
.cu-logout:hover { color: var(--compass); }
.compass-guest { font-size: 11px; color: var(--parchment-dim); }
```

- [ ] **步骤 3：修改 notify-log.js 显示审阅通知**

先 Read `frontend/static/components/notify-log.js`。现有逻辑按 type 显示图标/标签，追加审阅类型映射：

```javascript
// 在 notify-log.js 的 type 映射处追加
'task_submit': { label: '提交', class: 'nt-submit' },
'task_review': { label: '审阅', class: 'nt-review' },
```

并在 style.css 追加：

```css
.nt-submit { color: var(--compass); }
.nt-review { color: var(--brass); }
```

- [ ] **步骤 4：全流程冒烟测试**

启动后端，跑完整流程：
1. 注册队长 A + 创建项目 P1
2. 队长 A 生成邀请码
3. 注册队员 B + 用码加入 P1
4. 队长 A 分配任务给 B
5. 队员 B 提交产物
6. 队长 A 在成员进度页审阅通过
7. 队员 B 标记任务完成
8. 全程刷新页面，预期状态保持（token + hash 路由）
9. 登出，预期回登录页

- [ ] **步骤 5：Commit**

```bash
git add frontend/index.html frontend/static/style.css frontend/static/components/notify-log.js
git commit -m "feat: 罗盘栏用户信息显示 + 审阅通知集成"
```

---

## 自检

**1. 规格覆盖度：**
- 身份认证（注册/登录/登出/join）→ 任务 1、3、4 ✓
- 多项目管理（列表按用户过滤）→ 任务 4、9 ✓
- 任务认领与分配 → 任务 5、6、10 ✓
- 任务审阅（提交/审阅/下载）→ 任务 5、6、10、11 ✓
- 成员进度视图 → 任务 6、11 ✓
- 权限矩阵 → 任务 2、5、6、7 ✓
- 通知集成 → 任务 5（_notify_leader）、12 ✓
- 现有数据兼容 → 任务 0（迁移幂等）✓
- 文件存储 → 任务 6（data/submissions）✓

**2. 占位符扫描：** 无 TODO/待定。任务 8 步骤 1 与任务 10 步骤 2 有"先 Read 现有文件再合并"的说明，这是执行指引不是占位。

**3. 类型一致性：**
- `deps.get_current_user(token)` 签名贯穿任务 2/4/6/7 ✓
- `models.assign_task(task_id, assignee_id)` 贯穿任务 5/6 ✓
- `review_service.submit_task(task_id, filename, filepath, member_token, project_id)` 贯穿任务 5/6 ✓
- `member_service.get_member_progress(project_id)` 任务 6 定义、任务 11 调用 ✓
- 前端 `parent.authHeaders()` / `parent.navigate()` / `parent.loadProject()` 贯穿任务 8-11 ✓

**4. 风险点：**
- 任务 5 步骤 2 的 `insert_notification` 签名需对齐现有 `notifications` 表，已在步骤说明中提示先 Read 确认
- 任务 9/10/11 的 CSS 变量名需对齐现有 style.css，已提示先 Grep 确认
- 任务 8 步骤 1 的 app.js 改造需保留现有方法，已提示先 Read 再合并

---

## 执行交接

计划已完成并保存到 `docs/superpowers/plans/2026-07-23-lightweight-collaboration.md`。两种执行方式：

**1. 子代理驱动（推荐）** - 每个任务调度一个新的子代理，任务间进行审查，快速迭代

**2. 内联执行** - 在当前会话中使用 executing-plans 执行任务，批量执行并设有检查点

选哪种方式？

