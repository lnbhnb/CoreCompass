# CoreCompass 设计文档

> 校园项目"伪需求"粉碎机 —— 项目拆解与进度管理 Agent
> 创建日期：2026-07-23
> 赛事：火山引擎 Trae 校赛（截止 2026-07-31）

## 一、作品定位

**一句话**：CoreCompass —— 校园项目"伪需求"粉碎机：一个像 GPS 一样会偏航重算、会硬核验收、会主动催办的项目拆解 Agent。

**目标用户**：参加创新创业大赛、数学建模、需完成大型期末小组项目的大学生团队。

**核心痛点**：学生拿到宏大课题（如"校园二手交易平台"）不知从何下手，缺乏把"大目标"拆解为"每日待办"的工程化思维，前期拖延、后期熬夜。

**定位纪律**：Agent 是"敏捷开发教练"，**不替学生写代码/写方案**（避免沦为作弊工具）。聚焦帮学生建立现代企业项目管理思维，契合大赛"提升工程实践技能"初衷。

## 二、参赛约束

- 工具：Trae（强制）
- 工期：solo 全力投入，8 天，零缓冲
- 截止：2026-07-31
- 交付：录屏 MP4 ≤50MB + 详细材料 PDF/DOC ≤5MB + PPT ≤20MB
- 评分：技术实现 30% + 实用价值 30% + 创新性 20% + 体验 20%

## 三、三个突出点（核心创新）

### 突出点 ①：实体验证（硬验收，反"AI 盲信用户"）

通用 AI 弱点：用户说"完成了"，AI 就信。CoreCompass 强制上传真实产物并结构化校验，未过校验进度锁定。

**校验路由（按文件类型分流）**

| 产物类型 | 校验方式 | 通过条件 |
|---|---|---|
| `.sql`（数据库设计里程碑） | `sqlparse` 解析 → 查 CREATE TABLE / PRIMARY KEY / FOREIGN KEY | ≥2 张表 + ≥1 主键 + ≥1 外键 |
| `.md`（需求文档/README） | 字数 + 结构标题（H2/H3）+ 关键词覆盖 | ≥500 字 + ≥3 个 H2 + 含必填关键词 |
| `.py/.js/.ts`（编码里程碑） | AST 解析（Python ast / JS esprima）→ 检查类/函数定义 | ≥2 个函数/类定义 + 非空实现 |
| `.json/.yaml`（API 设计） | schema 校验 | 含必填字段 |
| 其他/兜底 | LLM 结构化校验（返回 JSON `{pass, reasons}`） | LLM 判定 |

**降级**：解析失败 → 自动 fallback LLM 校验，保证 Demo 不卡死。

**闭环画面**：上传空 .sql → 红色 toast"缺少外键，进度锁定" → 上传合规 .sql → 绿色"通过，解锁下一阶段"，写入 `validation_records`。

### 突出点 ②：动态重算 + 砍需求（GPS 式导航）

通用 AI 给的是静态"死计划"，一旦拖延就作废。CoreCompass 像汽车导航，发现偏航自动重算。

**触发器**
- 自动：APScheduler 每日扫描 → 发现 `overdue` 任务 → 标记 Project 为 `crisis`
- 手动：任务看板"触发重规划"按钮（Demo 主用）

**重规划算法（确定性骨架）**
```
1. 收集所有未完成任务 + 预估工作量（人天）
2. 剩余产能 = 剩余天数 × 团队人数 × 0.6（有效工时系数）
3. 缺口 = 剩余工作量 − 剩余产能
4. if 缺口 ≤ 0: 仅顺延日期，不砍
5. if 缺口 > 0:
   - LLM 收到任务列表 + 缺口 + 优先级标签 → 输出砍/降级提案
   - 用户在 UI 确认 → 系统写入 cut 任务 + 重排剩余日期
   - Project 回到 active
```

**LLM 提案 Prompt 约束**：必须返回 JSON `{cut_tasks:[], downgrade_tasks:[{id, from, to}], rationale}`；只允许砍 `priority=optional` 任务，`core` 任务只能降级不能删。保证不会"砍光核心"暴雷。

**UI 画面**：触发 → 模态框显示"缺口 3.5 人天"+ LLM 提案 → 用户勾选确认 → 任务看板实时刷新（被砍任务灰显划线、降级任务标签变色）→ 进度条重算。

### 突出点 ③：主动打扰（事件驱动）

通用 AI 被动唤醒。CoreCompass 具备时间感知与事件触发，主动催办。

**飞书接入**：群里"添加自定义机器人"→ 拿 webhook URL + 可选签名密钥 → 后端 `feishu_client.py` 推送。

**触发场景（三类，Demo 各演一个）**
1. **逾期警告**：扫描 overdue 任务 → "@xxx，任务《前端页面》已逾期 2 天，剩余 6 天"
2. **里程碑临近**：距离里程碑验收 ≤48h 且未完成 → 推送提醒
3. **手动测试按钮**：`/api/notify/test` → 立即推送一条 Demo 通知（解决"定时无法现场发生"）

**调度**：APScheduler `IntervalTrigger`（Demo 设 1 分钟或手动触发）。推送结果写 `notifications` 表，前端通知日志面板实时展示。

**Demo 视觉冲击**：现场点击"测试推送" → 大屏飞书群几秒内弹出 Agent 催办 → 通知日志面板同步显示 → 评委秒懂"Agent 主动找人"。

## 四、整体架构

### 技术栈
- 后端：Python + FastAPI
- 前端：HTML + Alpine.js（轻量响应式）
- DB：SQLite
- 调度：APScheduler（进程内）
- LLM：豆包（火山引擎 SDK）
- 文件校验：sqlparse / Python ast / esprima / jsonschema
- 部署：本地或火山引擎

### 组件
- **前端面板**：项目创建 / 任务看板 / 上传验收 / 通知日志
- **后端路由组**：projects、tasks、checkin、validate、replan、notify
- **LLM 服务**：初始计划生成、重规划提案、文件结构化校验兜底
- **调度器**：每日扫描逾期 → 推飞书（③）；提供手动触发按钮

### 核心数据流（闭环）
1. 用户创建项目（名称/截止日/团队人数/课题描述）→ LLM 生成里程碑+周任务拆解，写入 DB（status=planned）
2. 每日打卡：用户更新任务状态 → 状态机推进
3. ① 里程碑关卡：强制上传产物 → 校验通过才解锁下一阶段
4. ② 重规划触发（调度检测逾期 or 手动）→ 状态机算剩余产能 → LLM 提砍需求方案 → 用户确认 → 任务重生
5. ③ 调度扫描逾期 → 飞书 webhook 推送

## 五、领域模型与状态机（② 的骨架，确定性）

```
Task:     planned → doing → done
          doing → overdue (过截止且未完成)
          any → cut (重规划时被砍)
Milestone: planned → in_progress → done
           产物未过校验时 → locked（阻塞下一里程碑）
Project:  active → crisis(触发重规划) → active(方案确认) → completed
```

**核心原则**：LLM 仅做"建议"，所有"决策"（状态推进/任务写入）由确定性代码执行。这是 ② 可靠性的根本，也是评委区分"AI 聊天工具" vs "工程化 Agent"的关键。

## 六、数据模型（SQLite）

```
projects
  id, name, deadline, team_size, topic_desc, status, created_at
  status: active | crisis | completed

milestones
  id, project_id(FK), name, order_idx, status, expected_artifact_type
  status: planned | in_progress | locked | done
  expected_artifact_type: sql | md | code | json | other

tasks
  id, milestone_id(FK), project_id(FK), title, description,
  priority: core | optional
  difficulty: high | mid | low
  est_effort_days, status, start_date, due_date, completed_at
  status: planned | doing | done | overdue | cut

checkins
  id, task_id(FK), note, created_at

validation_records
  id, milestone_id(FK), filename, file_type, result,
  fail_reasons(JSON), llm_used(bool), created_at
  result: pass | fail

replan_logs
  id, project_id(FK), gap_days, proposal(JSON), applied(bool), created_at

notifications
  id, project_id(FK), type, content, status, response, created_at
  type: overdue | milestone_due | manual_test
  status: sent | failed
```

**关键约束**：milestone.expected_artifact_type 决定 ① 校验路由；task.priority 决定 ② 砍/降级边界；所有状态变更写时间戳便于复盘。

## 七、错误处理

| 边界 | 处理 |
|---|---|
| LLM 调用失败/超时 | 重试 1 次（间隔 2s）→ 仍失败用预设模板兜底（初始计划/砍需求均有降级模板） |
| LLM 返回非 JSON | jsonrepair 修复 → 仍失败记录 replan_logs.applied=false，UI 提示"AI 提案失败，请手动调整" |
| 文件解析异常 | 自动 fallback LLM 校验 |
| 飞书 webhook 4xx/5xx | 记录 notifications.status=failed，前端红色展示，不阻塞主流程 |
| 飞书签名校验 | webhook URL 配置时一并配 secret，按飞书文档 HMAC-SHA256 签名 |
| APScheduler 任务异常 | try/except 包裹，错误写 notifications 表，不让调度器崩溃 |
| 文件大小/类型 | 上传限制 ≤10MB + 白名单扩展名，超限直接 400 |
| 截止日已过 | 创建项目校验 deadline > now；重规划时若剩余天数 ≤0 直接建议"砍到最小可演示版本" |

## 八、测试策略（TDD，与 8 天工期平衡）

**P0（必须，~1 天）**——支撑 Demo 主路径
- 状态机转换：planned→doing→done、doing→overdue、any→cut
- 重规划产能计算：缺口公式 + 砍 optional/降级 core 边界
- .sql 校验：空文件、缺外键、合规文件三类
- 里程碑锁定：未过校验无法解锁下一阶段

**P1（应做，~0.5 天）**——边界防护
- LLM JSON 修复/fallback 模板
- 飞书 webhook mock（不依赖真实网络）
- 文件上传白名单/大小限制

**P2（跳过）**——UI 交互、前端渲染、手动触发按钮（Demo 手测即可）

**技术**：pytest + httpx（FastAPI 异步测试）+ freezegun（冻结时间测逾期）+ monkeypatch LLM 调用。LLM 相关一律 mock，保证 CI 可重现。

## 九、Demo 脚本（三段式，评委视角）

1. **拆解**：输入"校园二手交易平台 / 30 天 / 3 人" → Agent 输出里程碑+周计划
2. **硬验收**：里程碑关卡上传空 .sql → 被打回锁定 → 上传合规 .sql → 通过解锁（突出点①）
3. **偏航重算**：手动标记任务逾期 → Agent 算出缺口 → 提砍需求方案 → 确认后任务看板重生（突出点②）+ 飞书群收到催办（突出点③）

## 十、范围与降级表（超时即降级，保 Demo 必走通）

| 模块 | 完整版 | 降级版（超时启用） |
|---|---|---|
| 初始计划生成 | LLM 生成里程碑+周任务 | 预置 3 套模板按课题类型选 |
| ① 实体验证 | 5 种文件类型路由校验 | 仅 .sql + LLM 兜底 |
| ② 重规划 | 状态机+产能计算+LLM 提案 | 仅规则砍 optional 任务（无 LLM 提案） |
| ③ 主动打扰 | 飞书 webhook + APScheduler | 仅手动测试按钮（无定时扫描） |
| 前端 | Alpine.js 完整看板 | Streamlit 粗版看板 |
| 测试 | P0+P1 | 仅 P0 |

## 十一、8 天排期（solo 全力，零缓冲）

| 日 | 任务 | 产出 |
|---|---|---|
| D1 | 项目脚手架 + SQLite 模型 + 状态机 + 初始计划生成（LLM） | 可创建项目、生成任务、跑通状态转换 |
| D2 | ① 实体验证：.sql 校验 + 上传 API + locked 机制 | 突出点①后端闭环 |
| D3 | ② 重规划：产能计算 + LLM 提案 + 任务重排 | 突出点②后端闭环 |
| D4 | ③ 主动打扰：飞书 webhook + APScheduler + 手动触发 | 突出点③闭环 |
| D5 | 前端：项目创建 + 任务看板 + 上传区 | 主路径 UI 可点 |
| D6 | 前端：重规划模态 + 通知日志 + 打卡 | 三突出点 UI 闭环 |
| D7 | P0 测试 + 集成打磨 + Demo 脚本走查 | 端到端可演示 |
| D8 | 录屏（≤50MB MP4）+ PPT + 详细材料 PDF | 三件套交付 |

**关键纪律**：
- D1-D4 每天结束必须后端闭环可测（前端用 curl/Postman 验证）
- D5-D6 前端先纵向薄片（创建→看板→上传三页走通）再补全
- 任何一天超时立即按降级表执行，不许加范围

## 十二、评分自检

- **技术实现 30%**：状态机 + 混合重规划（规则+LLM）+ 多类型文件校验 + 调度 ✓
- **实用价值 30%**：真实痛点 + 三闭环可演示 ✓
- **创新性 20%**：GPS 式重算叙事 + 硬验收（反"AI 盲信用户"）✓
- **体验 20%**：看板/模态/通知日志三面板 ✓
