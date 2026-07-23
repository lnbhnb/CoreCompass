# CoreCompass · 校园项目"伪需求"粉碎机

> 让 AI Agent 不再只会附和，而是真正把关你的项目进度。

**CoreCompass** 是一个面向高校学生团队的 AI 项目管理 Agent。它通过"真实状态机 + LLM"的混合架构，解决了通用 AI 聊天工具"只附和不把关"的痛点，让学生团队的大课题从"无从下手"走向"可控交付"。

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

- **SQL**：≥2 表、含 PRIMARY KEY、含 FOREIGN KEY
- **Markdown**：≥500 字、含 H2 标题、无 TODO 标记
- **Code**：AST 解析、含函数/类定义、非空
- **JSON/YAML**：语法可解析、schema 结构合理

> Notion、语雀只存文档不校验；通用 LLM 只对话不把关。CoreCompass 强制校验真实产物。

### 突出点② 动态重算（GPS 式重规划）

当检测到任务逾期或 deadline 临近，触发**三段式重规划**：

1. **规则层**：计算产能缺口 `gap = 剩余工作量 - 剩余天数 × 团队人数 × 0.6`
2. **LLM 层**：把缺口和任务列表喂给大模型，生成砍/降级提案
3. **铁律层**：拒绝砍 `core` 任务，强制砍最高工时的 `optional`

> 就像 GPS 检测到堵车会重新规划路线，CoreCompass 检测到进度偏航会重新规划任务。

### 突出点③ 主动打扰（反"被动响应"）

APScheduler 定时扫描逾期任务，按项目聚合后通过飞书 webhook **主动推送**。

- **定时**：默认每 60 分钟扫描一次
- **手动**：Demo 主路径 `/api/notify/test`
- **即时**：重规划应用后立即推送

> 飞书、钉钉的提醒依赖人触发；CoreCompass 的 Agent 主动巡检并推送。

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

### 5. Demo 三段式

1. **创建项目**：填入课题、截止日期、团队人数 → Agent 生成里程碑和任务
2. **硬验收**：在里程碑上传文件 → 不合规红色锁定 / 合规绿色通过
3. **动态重算**：点"模拟偏航" → 点"触发重规划" → 确认应用 → 看板刷新
4. **主动打扰**：点"测试推送飞书" → 飞书群收到 Agent 消息

## 测试

```bash
cd backend
pytest -v
```

29 个测试全绿，覆盖：状态机转换、5 类文件校验、产能计算、重规划铁律、飞书推送、LLM JSON 解析、端到端三段式闭环、边界用例。

## 项目结构

```
CoreCompass/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口
│   │   ├── config.py            # 环境配置
│   │   ├── db.py                # SQLite 初始化
│   │   ├── models.py            # 数据访问层
│   │   ├── state_machine.py     # 任务/里程碑/项目状态机
│   │   ├── routes/              # 5 个路由模块
│   │   │   ├── projects.py      # 项目 CRUD + 创建时拆解
│   │   │   ├── validate.py      # 硬验收
│   │   │   ├── replan.py        # 动态重算
│   │   │   ├── notify.py        # 主动打扰
│   │   │   └── tasks.py         # 任务打卡
│   │   ├── services/            # 4 个业务服务
│   │   │   ├── project_service.py
│   │   │   ├── validate_service.py
│   │   │   ├── replan_service.py
│   │   │   └── notify_service.py
│   │   └── llm/                 # LLM 客户端 + Prompts
│   ├── tests/                   # 29 个测试
│   └── requirements.txt
├── frontend/
│   ├── index.html               # 单页应用
│   └── static/
│       ├── app.js               # 主组件
│       ├── style.css
│       └── components/          # 5 个 Alpine.js 组件
└── 参赛材料/
    ├── Demo脚本.md
    ├── 录屏操作指引.md
    ├── PPT大纲.md
    ├── 详细材料草稿.md
    └── demo-files/              # Demo 测试文件
```

## 创新点对比

| 创新 | 与现有工具的差异 |
|---|---|
| 反 AI 盲信 | Notion/语雀只存文档不校验；通用 LLM 只对话不把关。CoreCompass 强制校验真实产物 |
| GPS 式重算 | Jira/Teambition 只显示逾期不主动决策；CoreCompass 自动算缺口 + LLM 提案 + 铁律保底 |
| 主动打扰 | 飞书/钉钉的提醒依赖人触发；CoreCompass 的 Agent 主动巡检并推送 |

## 落地价值

- **学生侧：** 零安装（浏览器访问），5 分钟上手
- **教师侧：** 可作为课程设计过程管理工具，查看团队真实进度
- **扩展性：** 校验器可插拔（新增类型只需实现 `validate_xxx`）；LLM 可替换（任何兼容 OpenAI 协议的模型）
- **成本：** SQLite 单文件、DeepSeek 按调用计费（一次 Demo 约 0.005 元）、飞书 webhook 免费

## License

MIT
