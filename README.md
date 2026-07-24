# CoreCompass · 校园项目进度护栏

> 规则 + LLM 混合架构：让大模型不再只会附和，而是用确定性状态机真正把关项目进度。

**CoreCompass** 是一个面向高校学生团队的进度护栏系统，采用"确定性状态机 + LLM"的混合架构，把通用 AI 聊天工具"只附和不把关"的痛点转化为可量化的进度约束，让学生团队的大课题从"无从下手"走向"可控交付"。

> **定位说明**：CoreCompass 不是通用 AI Agent，而是"LLM 辅助 + 规则护栏"的项目管理工具。LLM 仅在初始拆解和重规划提案两处参与决策；所有状态转移、产物校验、任务锁定均由确定性代码强制约束，避免 LLM 失控或幻觉影响项目状态。

## 它解决什么问题？

学生拿到一个月以上的大课题（课程设计、毕设、创新竞赛），普遍面临三大困境：

| 困境 | 现状 | CoreCompass 的解法 |
|---|---|---|
| **AI 盲信** | ChatGPT/豆包顺着用户说话，不验证是否真的产出 | **硬验收**：强制校验真实产物，不通过就锁进度 |
| **不会重规划** | 延期只会加夜班，不懂砍需求 | **动态重算**：算产能缺口 + LLM 砍需求提案 + 铁律校验 |
| **被动协作** | 所有工具靠主动查询，没人主动催 | **主动打扰**：定时扫描逾期 + 飞书 webhook 推送 |

## 三大突出点

### 突出点① 硬验收（反"AI 盲信"）

每个里程碑声明 `expected_artifact_type`（sql / md / code / json / yaml），上传产物后由对应校验器做**结构化校验**，不通过则里程碑 `locked`，无法进入下一阶段。

- **SQL**：≥2 表、含 PRIMARY KEY、含 FOREIGN KEY、每表必须有列定义（拒绝空壳表）
- **Markdown**：≥500 字、含 ≥3 H2 标题、含"需求/功能/用户"关键词、去重率 < 60%（拒绝凑字数）
- **Code**：AST 解析、含 ≥2 函数/类定义、函数体非空、源码 ≥50 字符
- **JSON/YAML**：语法可解析、顶层为对象、必含 `name` 和 `endpoints`

> Notion、语雀只存文档不校验；通用 LLM 只对话不把关。CoreCompass 强制校验真实产物。

#### 与 CI / lint 的区别（评委常问）

| 维度 | GitHub Actions / lint | **CoreCompass 硬验收** |
|---|---|---|
| 校验对象 | 代码本身（语法、单测、风格） | 项目产物（需求文档、数据库 schema、API 设计稿） |
| 触发时机 | commit / push | 里程碑节点（与项目阶段绑定） |
| 失败后果 | 阻塞合并请求 | **状态机锁定**，无法进入下一阶段 |
| 校验维度 | 代码质量 | 产物结构完整性（SQL 表数/外键、MD 字数/标题层级） |

CoreCompass 不替代 CI，而是在 CI 之前的"项目产物阶段"做门禁，与 CI 形成互补。

### 突出点② 产能缺口检测（规则驱动，LLM 辅助）

当检测到任务逾期或 deadline 临近，触发**规则驱动的产能缺口检测 + LLM 辅助提案**：

1. **规则层（主决策）**：计算产能缺口 `gap = 剩余工作量 - 剩余天数 × 团队人数 × 0.6`；`gap > 0` 才触发后续流程
2. **LLM 层（仅辅助提示）**：把缺口和任务列表喂给大模型，生成砍/降级**建议**（非决策）
3. **铁律层（最终决策）**：拒绝砍 `core` 任务，强制砍最高工时的 `optional`；LLM 建议不强制采纳

> **定位说明**：与"AI 自动决策"不同，CoreCompass 的重规划是**规则层做最终决策**，LLM 仅提供人话化的建议文案，最终是否采纳由队长确认。即使 LLM 失败，规则层仍可独立完成强制砍需求。

#### 0.6 效率系数依据（评委常问）

参考校园团队实际有效产出测算：
- 学生日均可投入工时 ≈ 8 小时
- 扣除上课（≈4h）、考试周缓冲、社交、通勤等无效时段，**有效产出约 5 小时**
- 取整系数 `5 / 8 ≈ 0.6`

该系数可在 [backend/app/services/replan_service.py](backend/app/services/replan_service.py) 的 `EFFICIENCY_FACTOR` 处校准（竞赛冲刺期可调至 0.8，期末考试期可调至 0.3）。规则层始终先于 LLM 计算，缺口为 0 或负数时不触发 LLM 提案，避免无谓调用。

### 突出点③ 主动打扰（反"被动响应"）

APScheduler 定时扫描逾期任务，按项目聚合后通过飞书 webhook **主动推送**。

- **定时**：默认每 60 分钟扫描一次
- **手动**：Demo 主路径 `/api/notify/test`
- **即时**：重规划应用后立即推送

> 飞书、钉钉的提醒依赖人触发；CoreCompass 的 Agent 主动巡检并推送。

## 团队协作（轻量协作版）

在三大核心卖点之上，内置轻量协作能力，无需复杂部署即可让小团队用起来：

| 能力 | 说明 |
|---|---|
| 身份认证 | 注册/登录，PBKDF2 密码哈希，随机 token 存 DB |
| 角色权限 | 队长（建项目/分配任务/审阅/生成邀请码）、队员（认领/提交产物/看进度）严格分工 |
| 多项目管理 | 一个用户可参与多个项目，按 `project_members` 关联 |
| 邀请码加入 | 队长生成 6 位邀请码（7 天有效），队员注册后输码加入项目 |
| 任务审阅 | 队员提交产物 → 队长审阅（通过/拒绝）→ 通知，与里程碑自动验收独立并行 |
| 成员进度 | 队长看全队完成率 + 待审阅队列；队员只看自己 |

> 任务审阅管"人有没有认真做"，里程碑校验管"产物结构合不合规"，两者互不阻塞。

## 目标用户

- **主要用户：** 高校学生团队（3-5 人），参加课程设计、毕业设计、创新竞赛
- **次要用户：** 指导教师，可作为过程管理工具查看团队真实进度

## 技术架构

```
浏览器（Alpine.js）
    ↓ HTTP
FastAPI（路由 + 中间件）
    ├── 项目服务（创建 + LLM 初始拆解）
    ├── 校验服务（5 类文件结构化校验）
    ├── 重规划服务（规则 + LLM + 铁律）
    ├── 通知服务（飞书 webhook + APScheduler）
    └── 状态机（任务/里程碑/项目确定性转移）
    ↓
SQLite（项目 / 任务 / 里程碑 / 校验记录 / 通知日志）
    ↓
DeepSeek LLM（OpenAI 协议，带重试 + JSON 修复 + fallback）
```

| 层 | 选型 | 理由 |
|---|---|---|
| 后端 | FastAPI | 轻量、异步、自带 API 文档 |
| 数据库 | SQLite | 零配置、单文件、便于 Demo |
| 前端 | Alpine.js | 无构建步骤、CDN 引入、响应式 |
| 调度 | APScheduler | Python 生态成熟、后台守护进程 |
| LLM | DeepSeek（兼容 OpenAI 协议） | 可替换为豆包/GPT 等任何兼容模型 |

## 核心算法

### 状态机
任务五态确定性转移：`planned → doing → done` / `doing → overdue` / `任意 → cut`。非法转换抛 `InvalidTransition`，由 `transition_task()` 强制约束。

### 产能缺口公式
```
gap = Σ(est_effort_days × 未完成率) - remaining_days × team_size × 0.6
```
效率系数 0.6 反映校园团队实际产出（扣除上课、考试、社交时间）。

### LLM JSON 修复
三层兜底：`json.loads` → `json_repair` 库 → 正则提取代码块。确保 LLM 返回格式异常时仍能解析。

## 快速开始

### 1. 环境准备

- Python 3.10+
- DeepSeek API Key（或任何兼容 OpenAI 协议的 LLM）
- 飞书自定义机器人 Webhook（可选，不配则跳过推送）

### 2. 配置

```bash
cd backend
cp .env.example .env
```

编辑 `.env`：
```env
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx
DEEPSEEK_BASE_URL=https://api.deepseek.com
VOLC_MODEL=deepseek-chat

FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxx
FEISHU_SECRET=your_signing_secret

SCHEDULER_INTERVAL_MINUTES=60
```

### 3. 安装依赖

```bash
pip install -r backend/requirements.txt
```

### 4. 启动

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

浏览器打开 http://localhost:8000

### 5. Demo 四段式

1. **创建项目**：注册队长 → 填入课题、截止日期、团队人数 → Agent 生成里程碑和任务
2. **团队协作**：成员进度页生成邀请码 → 队员注册输码加入 → 分配/认领/提交/审阅任务
3. **硬验收**：在里程碑上传文件 → 不合规红色锁定 / 合规绿色通过
4. **动态重算**：点"模拟偏航" → 点"触发重规划" → 确认应用 → 看板刷新
5. **主动打扰**：点"测试推送飞书" → 飞书群收到 Agent 消息

## 使用范例

### 范例 1：校园二手交易平台（Web 后端项目）

**输入：**
- 项目名：校园二手交易平台
- 截止日期：2026-08-20
- 团队人数：3
- 课题描述：校园二手交易平台，支持学生发布闲置物品、浏览搜索、模拟交易，web 后端项目

**Agent 行为：**
1. 匹配知识库：SDLC 混合模型 + Flask/Django 项目里程碑（课题含"web/交易"）
2. 生成 4-6 里程碑：需求分析 → 数据库设计 → 核心实现 → 测试部署
3. 每个里程碑声明验收类型（md / sql / code）
4. 你上传空 SQL → 红色拒绝，里程碑 locked
5. 你上传合规 SQL（含表+主键+外键）→ 绿色通过，解锁下一阶段
6. 点"模拟偏航" → 点"触发重规划" → Agent 砍掉 optional 任务，core 保留
7. 点"测试推送飞书" → 飞书群收到 Agent 催办消息

### 范例 2：微信小程序（跨端项目）

**输入：**
- 课题描述：校园外卖小程序，微信端点餐、支付模拟、订单跟踪

**Agent 行为：**
1. 匹配知识库：SDLC 混合模型 + Taro 项目里程碑（课题含"小程序"）
2. 生成里程碑：环境搭建 → UI 组件 → 数据接口 → 业务功能 → 多端发布

### 范例 3：比赛项目（挑战杯）

**输入：**
- 课题描述：准备挑战杯创业计划，做一个校园共享雨伞项目

**Agent 行为：**
1. 匹配知识库：SDLC 混合模型 + 挑战杯赛程（课题含"挑战杯"）
2. 生成里程碑按赛程倒推：选题立项 → 方案设计 → 原型开发 → 成果优化 → 答辩材料

### 范例 4：纯 API 服务（无前端）

**输入：**
- 课题描述：图书管理 RESTful API，提供增删改查接口

**Agent 行为：**
1. 匹配知识库：SDLC 混合模型 + FastAPI 项目里程碑（课题含"api"）
2. 生成里程碑：骨架 → 数据层 → 业务接口 → 认证 → 测试文档

### 日常使用流程

```
创建项目 → 看到拆解计划 → 开始做任务 → 上传产物验收
  → 进度偏航？ → 触发重规划 → Agent 砍需求 → 继续
  → 飞书群定时收到 Agent 催办 → 完成所有里程碑 → 项目交付
```

## 知识库

项目内置结构化知识库（`knowledge_base/`），为 LLM 拆解提供真实素材支撑：

| 类别 | 内容 | 来源 |
|---|---|---|
| SDLC 模型 | 瀑布 / 敏捷 / 混合（校园推荐） | IEEE 830 / Scrum Guide |
| 开源项目里程碑 | Flask / FastAPI / Django / Taro | GitHub Milestones 公开数据 |
| 比赛日程 | 挑战杯 / 互联网+ / 计算机设计 | 各比赛官网公开赛程 |

**工作机制：** 创建项目时，Agent 按课题关键词匹配相关素材，注入 LLM Prompt 作为 few-shot 例子。看板顶部会显示"本次拆解参考了 XXX"，让拆解过程可追溯。

## 测试

```bash
cd backend
pytest -v
```

67 个测试全绿，覆盖：状态机转换、5 类文件校验、产能计算、重规划铁律、飞书推送、LLM JSON 解析、端到端三段式闭环、边界用例、知识库匹配、用户认证、权限校验、邀请码、任务审阅。

## 项目结构

```
CoreCompass/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口
│   │   ├── config.py            # 环境配置
│   │   ├── db.py                # SQLite 初始化 + 字段迁移
│   │   ├── models.py            # 数据访问层（项目/任务/里程碑/用户/成员/邀请码/审阅）
│   │   ├── state_machine.py     # 任务/里程碑/项目/审阅 状态机
│   │   ├── deps.py              # 认证与权限依赖（require_member/require_leader）
│   │   ├── routes/              # 8 个路由模块
│   │   │   ├── projects.py      # 项目 CRUD + 创建时拆解
│   │   │   ├── validate.py      # 硬验收
│   │   │   ├── replan.py        # 动态重算
│   │   │   ├── notify.py        # 主动打扰
│   │   │   ├── tasks.py         # 任务打卡（带鉴权）
│   │   │   ├── auth.py          # 注册/登录/登出/加入项目
│   │   │   ├── reviews.py       # 任务分配/认领/提交/审阅
│   │   │   └── members.py       # 邀请码/成员列表/进度统计
│   │   ├── services/            # 7 个业务服务
│   │   │   ├── project_service.py
│   │   │   ├── validate_service.py
│   │   │   ├── replan_service.py
│   │   │   ├── notify_service.py
│   │   │   ├── auth_service.py  # PBKDF2 哈希 + token
│   │   │   ├── member_service.py# 邀请码 + 进度统计
│   │   │   └── review_service.py# 任务审阅流转
│   │   └── llm/                 # LLM 客户端 + Prompts
│   ├── tests/                   # 67 个测试
│   └── requirements.txt
├── frontend/
│   ├── index.html               # 单页应用（航海罗盘仪表风格）
│   └── static/
│       ├── app.js               # 主组件（hash 路由 + 鉴权状态）
│       ├── style.css
│       └── components/          # 9 个 Alpine.js 组件
│       ├── auth.js              # 登录/注册/加入
│       ├── project-list.js      # 项目列表
│       ├── project-create.js    # 创建项目
│       ├── task-board.js        # 任务看板
│       ├── task-assign.js       # 分配/认领/提交/审阅
│       ├── member-progress.js   # 成员进度+邀请码
│       ├── upload-panel.js      # 里程碑上传
│       ├── replan-modal.js      # 重规划弹窗
│       └── notify-log.js        # 通知日志
└── knowledge_base/              # 结构化知识库
```

## 创新点对比

CoreCompass 与主流工具的差异（评委常问"这不就是 XX 吗？"）：

| 维度 | Notion / 语雀 | 飞书 / 钉钉任务 | GitHub Projects | GitHub Actions / CI | **CoreCompass** |
|---|---|---|---|---|---|
| 校验产物结构 | ❌ 只存文档 | ❌ 只跟踪任务 | ❌ 只看 issue | ✅ 但只校验代码 | ✅ 跨 5 类产物（sql/md/code/json/yaml） |
| 校验失败锁进度 | ❌ | ❌ | ❌ | ❌（仅阻塞合并） | ✅ 状态机锁定下一阶段 |
| 产能缺口检测 | ❌ | ❌ | ❌ | ❌ | ✅ 规则层算缺口 + LLM 辅助建议 + 铁律保底 |
| 主动巡检 + 推送 | 部分（手动） | 部分（机器人需触发） | ❌ | ❌ | ✅ APScheduler + 飞书 webhook |
| 适配学生竞赛场景 | 通用 | 通用 | 偏工程 | 偏工程 | ✅ 知识库注入赛程 / SDLC / 相似项目 |
| 校园团队效率系数 | ❌ | ❌ | ❌ | ❌ | ✅ 0.6 校准系数 |

**一句话定位**：CoreCompass 不是 Notion / 飞书 / GitHub Actions 的替代品，而是把它们都没做好的"产物结构门禁 + 进度偏航重规划"环节补齐，专注校园竞赛场景。

## 离线降级（Demo 兜底）

当 LLM API 或飞书 webhook 不可达时，CoreCompass 自动降级，确保主流程不中断：

| 故障点 | 降级行为 |
|---|---|
| LLM API（DeepSeek）不可达 | 项目拆解使用预设模板（SDLC 混合模型 + 通用里程碑），重规划只走规则层（强制砍最高工时 optional） |
| 飞书 webhook 不可达 | 通知仅写入 DB 日志（`notifications` 表），状态记为 `failed`，不影响主流程 |
| SQLite 文件损坏 | 启动时 `init_db()` 幂等重建 schema，仅丢失数据不阻断服务启动 |

**现场 Demo 兜底建议**：录屏 + 离线降级模式双保险。若现场网络异常，可关闭 `.env` 中的 `DEEPSEEK_API_KEY` 演示降级模式，再切回在线模式重放完整流程。

## 安全说明（Demo 版限制）

本项目为比赛 Demo，安全性做了基础处理但未达生产级：

- ✅ **密码哈希**：PBKDF2-HMAC-SHA256 + 16 字节随机盐 + 100,000 次迭代（[auth_service.py](backend/app/services/auth_service.py)）
- ✅ **邀请码防爆破**：6 位 + 7 天有效 + 失败 5 次锁定 15 分钟（[member_service.py](backend/app/services/member_service.py)）
- ✅ **登录 token 过期**：7 天有效期，过期自动失效
- ✅ **常量时间比较**：`secrets.compare_digest` 防 timing attack
- ⚠️ **未启用 HTTPS / CSRF 防护**——部署时需在反向代理层（Nginx / Caddy）补齐
- ⚠️ **token 明文存 DB**——Demo 简化处理，生产应使用 Redis + 加密存储

## 协作流程的语义边界

任务审阅与里程碑校验是**两条独立并行**的流水线，互不阻塞：

| 流水线 | 责任人 | 关注点 | 状态机 |
|---|---|---|---|
| 任务审阅 | 队长 | 队员**有没有认真做**（人审） | `pending_review → approved / rejected` |
| 里程碑校验 | 系统 | 产物**结构合不合规**（机审） | `planned → done / locked` |

**为什么独立**：人审通过不代表产物结构合规（队长可能放水），机审通过也不代表队员认真做了（可能凑数）。两条线交叉验证，降低单点失守风险。

## 落地价值

- **学生侧：** 零安装（浏览器访问），5 分钟上手
- **教师侧：** 可作为课程设计过程管理工具，查看团队真实进度
- **扩展性：** 校验器可插拔（新增类型只需实现 `validate_xxx`）；LLM 可替换（任何兼容 OpenAI 协议的模型）
- **成本：** SQLite 单文件、DeepSeek 按调用计费（一次 Demo 约 0.005 元）、飞书 webhook 免费

## License

MIT
