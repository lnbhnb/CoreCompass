# 轻量协作版设计文档（方案 B · 简单认证 + 任务审阅）

## 背景

当前 CoreCompass 是"单用户、单项目视图、无身份"的 demo 形态：无 users 表、无登录、`tasks` 无 assignee 字段、前端刷新即丢当前项目。要做"轻量协作版"，核心缺口是三块：成员模型 + 任务认领 + 多项目切换，身份认证作为加项。本设计在方案 A（无登录轻量版）基础上增加简单 token 认证与邀请码加入流程，并并入任务审阅机制（与现有里程碑自动验收独立并行）。

## 目标

1. **身份认证** —— 注册/登录/邀请码加入，随机 token 存 DB
2. **多项目管理** —— 队长看自己建的，队员看加入的，刷新不丢当前项目
3. **任务认领与分配** —— 队长分配，队员认领，看板显示负责人
4. **任务审阅** —— 队员提交产物 → 队长审阅，与里程碑自动验收独立并行
5. **成员进度视图** —— 队长看全队完成率，队员看自己

## 不做（YAGNI）

- 不做 JWT / OAuth / 第三方登录（随机 token 够用）
- 不做完整 RBAC 权限树（仅队长/队员两角色，硬编码权限矩阵）
- 不做邮件验证 / 找回密码（校园 demo 用不上）
- 不做任务审阅替代里程碑验收（保护突出点①的自动校验叙事）
- 不做实时协作 / WebSocket（轮询或手动刷新够用）

## 架构

```
注册/登录 → 随机 token 存 users.token
              ↓
         Authorization: Bearer {token}
              ↓
         鉴权中间件 → 注入 current_user
              ↓
    ┌─────────────┴─────────────┐
    队长                          队员
    ├─ 创建项目                  └─ 输邀请码加入项目
    ├─ 生成邀请码                    ↓
    ├─ 分配任务给队员           共享看板（按权限渲染）
    ├─ 触发重规划                    ↓
    ├─ 里程碑自动验收           任务层（人工审阅）
    └─ 审阅队员提交             ├─ 队员 submit 产物
                               └─ 队长 review（approved/rejected）
```

任务审阅与里程碑验收两层各自闭环，互不阻塞：
- **任务层（人工）**：队员 submit → 队长 review → approved 任务可标记 done
- **里程碑层（自动）**：队长 upload → 校验器自动判 → pass 解锁下一阶段

## 数据模型

### 新增表

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
  role TEXT NOT NULL DEFAULT 'member',  -- 'leader' | 'member'
  joined_at TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE(project_id, user_id)
);

CREATE TABLE IF NOT EXISTS invite_codes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  code TEXT NOT NULL UNIQUE,            -- 6 位大写字母数字
  used_by_user_id INTEGER REFERENCES users(id),
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  expires_at TEXT NOT NULL              -- 创建后 7 天
);
```

### tasks 表加列

```sql
ALTER TABLE tasks ADD COLUMN assignee_id INTEGER REFERENCES users(id);  -- 可空
ALTER TABLE tasks ADD COLUMN review_status TEXT;  -- pending_review/approved/rejected/NULL
ALTER TABLE tasks ADD COLUMN submission_filename TEXT;
ALTER TABLE tasks ADD COLUMN submission_path TEXT;
ALTER TABLE tasks ADD COLUMN reviewed_by INTEGER REFERENCES users(id);
ALTER TABLE tasks ADD COLUMN reviewed_at TEXT;
ALTER TABLE tasks ADD COLUMN review_comment TEXT;
```

### projects 表加列

```sql
ALTER TABLE projects ADD COLUMN creator_id INTEGER REFERENCES users(id);  -- 队长
```

### 现有数据兼容

- 旧项目 `creator_id = NULL` → 标记"无主项目"，首个注册用户可在项目列表页"认领"为队长（demo 场景下手动处理）
- 旧任务 `assignee_id = NULL` 且 `review_status = NULL` → 看板显示"未分配"，队长可补分配

## 认证流程

```
注册  POST /api/auth/register {username, password, display_name}
      → password_hash = pbkdf2_hmac('sha256', password, salt, 100000)
      → token = secrets.token_hex(32)
      → 返回 {user: {id, username, display_name}, token}

登录  POST /api/auth/login {username, password}
      → 校验 password_hash
      → 返回 {user, token}

登出  POST /api/auth/logout  (需 token)
      → users.token = NULL

邀请  队长 POST /api/projects/{pid}/invites  (需 leader 权限)
      → code = 6 位大写字母数字随机
      → 返回 {code, expires_at}

加入  队员 POST /api/auth/join {invite_code}  (需 token)
      → 校验码有效 + 未过期 + 未使用
      → INSERT project_members(role='member')
      → 标记 invite_codes.used_by_user_id

鉴权  所有需身份的请求带 Authorization: Bearer {token}
      → FastAPI Dependency: get_current_user
      → 查 users WHERE token=?，注入 current_user
      → 无 token / token 无效 → 401
```

**密码存储**：用 `hashlib.pbkdf2_hmac` + per-user salt，不引入 bcrypt 依赖。

**token 生命周期**：长期有效，登出清空 `users.token`，前端清 localStorage。

## 权限矩阵

| 操作 | 队长 | 队员 | 实现 |
|---|:---:|:---:|---|
| 创建项目 | ✓ | ✓ | 任意已登录用户可创建；创建者自动成为该项目的 leader |
| 生成邀请码 | ✓ | ✗ | `require_leader(pid)` 依赖 |
| 分配任务给队员 | ✓ | ✗ | `require_leader(pid)` |
| 触发重规划 | ✓ | ✗ | `require_leader(pid)` |
| 里程碑自动验收 | ✓ | ✗ | `require_leader(pid)` |
| 审阅任务提交 | ✓ | ✗ | `require_leader(pid)` |
| 标记自己任务进度 | ✓ | ✓ | `require_assignee(task_id)` 或 leader |
| 提交自己任务产物 | ✓ | ✓ | `require_assignee(task_id)` |
| 认领未分配任务 | ✗ | ✓ | 队员专属 |
| 查看项目看板 | ✓ | ✓ | `require_member(pid)` |
| 成员进度视图 | 全队 | 仅自己 | 按角色过滤返回数据 |

权限依赖函数：
- `get_current_user` → 返回 user 或 401
- `require_member(pid)` → 校验 user 在 project_members 中
- `require_leader(pid)` → 校验 role='leader'
- `require_assignee(task_id)` → 校验 user.id == task.assignee_id

## 路由清单

### 新增

```
POST   /api/auth/register
POST   /api/auth/login
POST   /api/auth/logout
POST   /api/auth/join                    {invite_code}
GET    /api/projects                     列出当前用户相关项目
POST   /api/projects/{pid}/invites       生成邀请码（leader）
GET    /api/projects/{pid}/members       列成员（member）
POST   /api/tasks/{id}/assign            {assignee_id}（leader）
POST   /api/tasks/{id}/claim             认领（member，任务须未分配）
POST   /api/tasks/{id}/submit            multipart: file（assignee）
POST   /api/tasks/{id}/review            {decision, comment}（leader）
GET    /api/tasks/{id}/submission        下载提交产物（leader 或 assignee）
GET    /api/projects/{pid}/progress      成员进度（按角色过滤）
```

### 修改

```
POST   /api/projects                     加 creator_id，创建者自动入 project_members 为 leader
GET    /api/projects/{pid}               返回含 used_references（现有）+ 当前用户角色
PATCH  /api/tasks/{id}/status            加权限校验（assignee 或 leader）
```

## 前端

### 视图状态机

```
view ∈ {login, projects, create, board, members}
```

hash 路由（无依赖）：
```
#/login                         → view='login'
#/projects                      → view='projects'
#/projects/new                  → view='create'
#/projects/{id}                 → view='board'
#/projects/{id}/members         → view='members'
```

刷新不丢项目：从 hash 读 projectId，token 存 localStorage。

### 罗盘栏适配

- 未登录：只显 brand + 底部"未登录"
- 已登录：brand + 罗盘环 + 导航项（项目列表/里程碑看板/成员进度/通知日志）+ 底部用户名+角色+登出

### 新增视图

**登录页**：居中卡片，复用 `.create-form-panel` 卡角刻度装饰。标题"启航前请登记"，eyebrow `AUTH · 01`。两 tab：登录/注册。注册多 `display_name`。底部小字"队员？向队长要邀请码"。另设"我有邀请码"入口（已登录用户加入新项目）。

**项目列表页**：卡片网格，每张卡显示序号（复用 `ms-index` 黄铜 mono 数字）、项目名、角色（队长/队员）、人数、`3/5 里程碑 · 12d 到岸`、小进度环。队长额外显示 `[+ 启动新航行]`，已登录用户显示 `[我有邀请码]`。

**成员进度视图**：
- 队长：成员卡片列表（负责人头像圆点 + 姓名 + 角色 + 负责/完成/审阅中/待办计数 + 罗盘橙进度条）+ 顶部"待我审阅（N）"区
- 队员：仅自己的卡片，无审阅区
- 审阅交互：点"查看产物"新开 tab 下载；"通过"直接通过；"拒绝"展开 textarea 写理由

### 看板视图增量

task-item 加一行：
```
[●] 任务标题  [进行中][核心]                    [开始][完成]
    @张三 · 待审阅                              [提交产物]
```
- 未认领：队长见"分配"按钮（弹成员选择）；队员见"认领"按钮
- 已认领：显示 `@负责人`
- 队员提交后：`@负责人 · 待审阅`（橙色），队长侧任务行高亮
- 审阅通过：`@负责人 · 已通过`（绿色）
- 审阅拒绝：`@负责人 · 需修改`（红色）+ 队长评论气泡

### 新增 Alpine 组件

```
frontend/static/components/
  auth.js              ← 登录/注册/加入
  project-list.js      ← 项目列表
  member-progress.js   ← 成员进度视图
  task-assign.js       ← 分配/认领/提交/审阅
```

修改：`project-create.js`（创建后回列表）、`task-board.js`（渲染 assignee + review_status）、`notify-log.js`（显示审阅通知）、`app.js`（路由 + 鉴权状态 + fetch 拦截器加 Authorization header）。

不变：`replan-modal.js`、`upload-panel.js`（里程碑验收仍是这个）。

### 装饰复用

不新增配色或字体，所有新元素从现有 token 派生：
- 登录卡 / 项目列表卡 / 成员卡：复用 milestone-card 四角刻度 + 悬停浮起
- 项目列表序号：复用 `ms-index`
- 成员进度条：罗盘橙填充 + 海图网格底
- 审阅状态色：`pending_review` 用 `--compass`、`approved` 用 `--pass`、`rejected` 用 `--fail`

### 响应式

- 登录页 / 项目列表：移动端单列
- 成员进度：移动端卡片堆叠，"待我审阅"置顶
- 看板任务行的 `@负责人 · 状态` 窄屏换行到第二行

## 文件存储

队员提交的产物存 `data/submissions/{task_id}_{timestamp}_{filename}`。不复用里程碑验收的 validate 路由（自动校验 vs 人工审阅，职责分开）。下载经 `/api/tasks/{id}/submission`，校验权限后返回 FileResponse。

## 通知集成

审阅相关事件写入 `notifications` 表，复用现有飞书推送：
- 队员 submit → 通知队长，`type='task_submit'`，内容"XX 提交了任务 YY，待审阅"
- 队长 approved → 通知队员，`type='task_review'`，内容"任务 YY 已通过"
- 队长 rejected → 通知队员，`type='task_review'`，内容"任务 YY 需修改：{comment}"

一个 user 可加入多个项目（project_members 多行），通知按 project_id 隔离。

## 测试策略

- `test_auth.py`：注册/登录/登出/join，密码校验，token 失效
- `test_permissions.py`：权限矩阵全覆盖（leader/member/未登录各操作）
- `test_task_review.py`：submit/review 流程，状态流转，权限校验
- `test_invite.py`：邀请码生成/过期/重复使用/加入
- 现有测试需适配：`test_project_service.py` 等补 creator_id 参数

## 现有架构影响

- `state_machine.py`：任务状态机加 `submit` / `review_pass` / `review_reject` 事件
- `services/`：新增 `auth_service.py`、`member_service.py`、`review_service.py`
- `routes/`：新增 `auth.py`、`members.py`、`reviews.py`；改 `projects.py`、`tasks.py`
- `models.py`：加 users/project_members/invite_codes CRUD + tasks 新字段
- `schema.sql`：加 3 张表 + 3 处 ALTER
- 前端 `app.js`：加 hash 路由 + fetch 拦截器（自动带 token）+ 鉴权状态
