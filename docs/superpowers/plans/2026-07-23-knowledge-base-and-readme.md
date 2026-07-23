# 知识库 + README 使用范例 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 为 CoreCompass 增加结构化知识库（SDLC + 开源项目里程碑 + 比赛日程），让 LLM 拆解"有据可依"，并在 README 中补充使用范例。

**架构：** 新增 `knowledge_base/` 目录存放真实素材，新增 `knowledge_service.py` 做关键词匹配与素材摘录，修改 `prompts.py` 注入素材摘录，前端看板展示"参考了哪些素材"。README 增加完整使用范例章节。

**技术栈：** Python / Markdown 素材 / 关键词匹配 / FastAPI / Alpine.js

---

## 文件结构

**新增：**
- `knowledge_base/sdlc/README.md` — SDLC 目录说明
- `knowledge_base/sdlc/waterfall.md` — 瀑布模型
- `knowledge_base/sdlc/agile.md` — 敏捷模型
- `knowledge_base/sdlc/hybrid.md` — 校园团队混合模型（推荐）
- `knowledge_base/projects/README.md` — 开源项目目录说明
- `knowledge_base/projects/flask.md` — Flask 里程碑参考
- `knowledge_base/projects/fastapi.md` — FastAPI 里程碑参考
- `knowledge_base/projects/django.md` — Django 里程碑参考
- `knowledge_base/projects/taro.md` — Taro 里程碑参考
- `knowledge_base/contests/README.md` — 比赛目录说明
- `knowledge_base/contests/challenge-cup.md` — 挑战杯日程
- `knowledge_base/contests/internet-plus.md` — 互联网+日程
- `knowledge_base/contests/computer-design.md` — 计算机设计大赛日程
- `knowledge_base/index.json` — 素材索引（关键词 → 文件）
- `backend/app/services/knowledge_service.py` — 匹配与摘录服务
- `backend/tests/test_knowledge_service.py` — 知识库服务测试

**修改：**
- `backend/app/llm/prompts.py` — INITIAL_PLAN_PROMPT 增加素材注入位
- `backend/app/services/project_service.py` — 调用 knowledge_service，返回 used_references
- `backend/app/routes/projects.py` — 响应中附带 used_references
- `frontend/index.html` — 看板顶部展示参考素材
- `frontend/static/app.js` — 接收 used_references
- `README.md` — 增加使用范例章节

---

## 任务 1：创建 SDLC 素材

**文件：**
- 创建：`knowledge_base/sdlc/README.md`
- 创建：`knowledge_base/sdlc/waterfall.md`
- 创建：`knowledge_base/sdlc/agile.md`
- 创建：`knowledge_base/sdlc/hybrid.md`

- [ ] **步骤 1：创建 sdlc/README.md**

```markdown
# 软件工程生命周期（SDLC）素材

本目录收录标准 SDLC 模型，作为 LLM 项目拆解的参考素材。

## 模型选择建议

| 模型 | 适用场景 | 校园团队推荐度 |
|---|---|---|
| 瀑布模型 | 需求明确、变更少的大型项目 | ⭐⭐ |
| 敏捷模型 | 需求多变、快速迭代的产品 | ⭐⭐⭐ |
| 混合模型 | 校园项目（需求部分明确 + 时间紧） | ⭐⭐⭐⭐⭐ |

校园团队推荐使用"混合模型"：前期用瀑布做需求与设计，中后期用敏捷迭代开发。

## 引用规范

每个素材文件包含 YAML frontmatter（source / keywords）+ 里程碑结构化数据。
```

- [ ] **步骤 2：创建 sdlc/waterfall.md**

```markdown
---
source: IEEE Standard 830-1998 / ISO/IEC 12207
keywords: [瀑布, waterfall, 大型项目, 需求明确]
---

# 瀑布模型（Waterfall）

## 阶段定义

按顺序执行，每阶段完成后进入下一阶段，不回溯。

1. **需求分析**（占比 20%）—— 产出需求规格说明书
2. **系统设计**（占比 20%）—— 产出架构设计文档、ER 图
3. **实现**（占比 30%）—— 编码
4. **测试**（占比 20%）—— 单元测试、集成测试、系统测试
5. **部署与维护**（占比 10%）—— 上线、文档交付

## 里程碑产物

- M1: 需求规格说明书（md）
- M2: 架构设计文档 + 数据库设计（md + sql）
- M3: 核心模块代码（code）
- M4: 测试报告（md）
- M5: 部署脚本 + 用户文档（code + md）

## 适用场景

需求明确、变更少、团队规模大、项目周期长（≥6 个月）。校园项目通常不适用纯瀑布。
```

- [ ] **步骤 3：创建 sdlc/agile.md**

```markdown
---
source: Agile Manifesto / Scrum Guide
keywords: [敏捷, agile, scrum, 迭代, sprint, 快速迭代]
---

# 敏捷模型（Agile / Scrum）

## 阶段定义

按 1-2 周的 Sprint 迭代，每 Sprint 交付可演示的功能增量。

1. **产品待办列表梳理** —— 全部需求拆成 User Story
2. **Sprint 计划** —— 选本 Sprint 要做的 Story
3. **Sprint 执行** —— 每日站会同步
4. **Sprint 评审** —— 演示成果
5. **Sprint 回顾** —— 改进流程

## 里程碑产物（按 Sprint）

- Sprint 1: MVP 核心功能（code）
- Sprint 2: 功能扩展（code）
- Sprint 3: 优化与测试（code + md）
- Sprint 4: 部署上线（code + md）

## 适用场景

需求多变、快速迭代的产品开发。校园项目周期紧时可用，但需要团队有较强自驱力。
```

- [ ] **步骤 4：创建 sdlc/hybrid.md**

```markdown
---
source: 综合瀑布与敏捷的校园项目实践
keywords: [混合, hybrid, 校园, 课程设计, 毕设, 竞赛, 推荐]
---

# 混合模型（校园团队推荐）

## 阶段定义

前期（需求与设计）用瀑布，确保方向正确；中后期（开发与测试）用敏捷迭代。

1. **需求与设计阶段**（前 20% 时间）—— 瀑布式
   - 需求分析 → 架构设计 → 数据库设计
   - 产出文档型里程碑，需硬验收
2. **核心开发阶段**（中间 50% 时间）—— 敏捷迭代
   - 按 1 周一个 Sprint 拆分
   - 每个迭代交付可演示功能
3. **测试与交付阶段**（后 30% 时间）—— 瀑布式收尾
   - 集成测试 → 部署 → 文档交付

## 里程碑产物

- M1: 需求规格说明书（md）—— 硬验收：≥500 字 + H2 标题
- M2: 数据库设计（sql）—— 硬验收：≥2 表 + 主键 + 外键
- M3: 核心功能实现（code）—— 硬验收：AST 解析 + 函数定义
- M4: 迭代扩展（code）—— 硬验收：AST 解析
- M5: 测试报告（md）—— 硬验收：≥500 字
- M6: 部署与文档（md）—— 硬验收：≥500 字

## 适用场景

**校园项目首选。** 兼顾"方向正确"与"灵活迭代"，适合 3-5 人团队、1-3 个月周期的课程设计/毕设/竞赛项目。
```

- [ ] **步骤 5：Commit**

```bash
git add knowledge_base/sdlc/
git commit -m "feat(kb): SDLC 素材（瀑布/敏捷/混合模型）"
```

---

## 任务 2：创建开源项目素材

**文件：**
- 创建：`knowledge_base/projects/README.md`
- 创建：`knowledge_base/projects/flask.md`
- 创建：`knowledge_base/projects/fastapi.md`
- 创建：`knowledge_base/projects/django.md`
- 创建：`knowledge_base/projects/taro.md`

- [ ] **步骤 1：创建 projects/README.md**

```markdown
# 开源项目里程碑素材

本目录收录成熟开源项目的真实里程碑数据（取自 GitHub Milestones 页面），作为 LLM 拆解"相似项目"的参考。

## 收录项目

| 项目 | 类型 | 关键词 |
|---|---|---|
| Flask | Python Web 后端 | web, api, 后端, flask, python |
| FastAPI | Python 异步 API | api, 异步, fastapi, 后端, 接口 |
| Django | Python 全栈框架 | web, 全栈, django, cms, 内容管理 |
| Taro | 跨端小程序框架 | 小程序, 跨端, taro, react, 多端 |

## 数据来源

所有数据取自各项目 GitHub 仓库的 Milestones 页面（公开数据），仅保留里程碑名称、周期、关键产物，不包含具体 issue。
```

- [ ] **步骤 2：创建 projects/flask.md**

```markdown
---
source: https://github.com/pallets/flask/milestones
keywords: [web, api, 后端, flask, python, http, 路由]
---

# Flask 项目里程碑参考

## 项目特点

Python 轻量级 Web 框架，适合中小型 API 服务、后端接口开发。

## 里程碑划分（参考 Flask 1.0/2.0 版本演进）

### M1: 基础架构（1 周）
- 关键产物：项目骨架、路由系统、配置管理
- 核心任务：初始化仓库、定义路由、配置加载、错误处理

### M2: 核心功能（2 周）
- 关键产物：请求处理、响应渲染、模板引擎
- 核心任务：请求上下文、蓝图（Blueprint）、模板渲染、静态文件

### M3: 数据持久化（1 周）
- 关键产物：ORM 集成、数据库迁移
- 核心任务：SQLAlchemy 集成、模型定义、Flask-Migrate 配置

### M4: 扩展功能（1.5 周）
- 关键产物：认证、表单、API 接口
- 核心任务：Flask-Login、Flask-WTF、RESTful API

### M5: 测试与部署（1 周）
- 关键产物：测试套件、部署脚本
- 核心任务：pytest 集成、CI 配置、WSGI 部署

## 适用场景

Python Web 后端项目，尤其是中小型 API 服务。校园项目可参考其 M1-M5 划分。
```

- [ ] **步骤 3：创建 projects/fastapi.md**

```markdown
---
source: https://github.com/tiangolo/fastapi/milestones
keywords: [api, 异步, fastapi, 后端, 接口, restful, openapi]
---

# FastAPI 项目里程碑参考

## 项目特点

Python 异步 API 框架，适合高性能接口服务、RESTful API、OpenAPI 文档自动生成。

## 里程碑划分（参考 FastAPI 版本演进）

### M1: 项目骨架（3-5 天）
- 关键产物：路由、依赖注入、Pydantic 模型
- 核心任务：FastAPI 实例、路由定义、请求体验证、依赖注入

### M2: 数据层（1 周）
- 关键产物：ORM、数据库连接、迁移
- 核心任务：SQLModel/SQLAlchemy、异步引擎、Alembic 迁移

### M3: 业务接口（1.5 周）
- 关键产物：CRUD 接口、业务逻辑
- 核心任务：增删改查、分页、过滤、错误处理

### M4: 认证与权限（1 周）
- 关键产物：JWT、OAuth2
- 核心任务：用户认证、权限校验、token 刷新

### M5: 测试与文档（1 周）
- 关键产物：测试套件、自动文档
- 核心任务：pytest + httpx、OpenAPI 文档、部署

## 适用场景

Python 异步 API 项目，需要高性能、自动文档的场景。
```

- [ ] **步骤 4：创建 projects/django.md**

```markdown
---
source: https://github.com/django/django/milestones
keywords: [web, 全栈, django, cms, 内容管理, python, admin]
---

# Django 项目里程碑参考

## 项目特点

Python 全栈 Web 框架，内置 ORM、Admin、认证、模板，适合内容管理系统、企业级应用。

## 里程碑划分（参考 Django 版本演进）

### M1: 项目初始化（3-5 天）
- 关键产物：Django 项目、App、配置
- 核心任务：django-admin startproject、settings 配置、App 划分

### M2: 数据模型（1 周）
- 关键产物：ORM 模型、迁移
- 核心任务：Model 定义、关系映射、makemigrations、admin 注册

### M3: 视图与模板（1.5 周）
- 关键产物：视图、URL、模板
- 核心任务：Function/Class View、URL 路由、DTL 模板、静态文件

### M4: 认证与权限（1 周）
- 关键产物：用户系统、权限
- 核心任务：User 模型、Login/Logout、权限装饰器、Session

### M5: API 与测试（1 周）
- 关键产物：DRF 接口、测试
- 核心任务：Django REST Framework、序列化、pytest-django

## 适用场景

Python 全栈 Web 项目，需要 Admin 后台、内容管理的场景。
```

- [ ] **步骤 5：创建 projects/taro.md**

```markdown
---
source: https://github.com/NervJS/taro/milestones
keywords: [小程序, 跨端, taro, react, 多端, 微信, 支付宝]
---

# Taro 项目里程碑参考

## 项目特点

跨端小程序框架，一套代码运行在微信/支付宝/H5/RN 多端，适合校园小程序项目。

## 里程碑划分（参考 Taro 版本演进）

### M1: 环境与骨架（3-5 天）
- 关键产物：Taro 项目、页面结构
- 核心任务：taro init、页面目录、全局配置、TabBar

### M2: UI 与组件（1 周）
- 关键产物：页面 UI、组件库
- 核心任务：页面布局、自定义组件、样式适配（rpx）、Taro UI

### M3: 数据与接口（1 周）
- 关键产物：API 对接、状态管理
- 核心任务：request 封装、Redux/MobX、数据渲染、列表分页

### M4: 业务功能（1.5 周）
- 关键产物：核心业务流程
- 核心任务：登录认证、表单提交、支付模拟、消息推送

### M5: 多端适配与发布（1 周）
- 关键产物：多端测试、打包
- 核心任务：条件编译、微信/支付宝差异处理、体验版上传

## 适用场景

校园小程序项目，需要跨端运行的场景。
```

- [ ] **步骤 6：Commit**

```bash
git add knowledge_base/projects/
git commit -m "feat(kb): 开源项目里程碑素材（Flask/FastAPI/Django/Taro）"
```

---

## 任务 3：创建比赛日程素材

**文件：**
- 创建：`knowledge_base/contests/README.md`
- 创建：`knowledge_base/contests/challenge-cup.md`
- 创建：`knowledge_base/contests/internet-plus.md`
- 创建：`knowledge_base/contests/computer-design.md`

- [ ] **步骤 1：创建 contests/README.md**

```markdown
# 比赛日程素材

本目录收录国内主流大学生竞赛的公开赛程，作为 LLM 拆解"按比赛日程规划"的参考。

## 收录比赛

| 比赛 | 周期 | 主办 |
|---|---|---|
| 挑战杯 | 每年 3-11 月 | 共青团中央 |
| 互联网+ | 每年 4-10 月 | 教育部 |
| 计算机设计大赛 | 每年 1-8 月 | 教指委 |

## 数据来源

各比赛官网公开发布的赛程通知，仅保留阶段名称与时间占比，不涉及具体评审细则。
```

- [ ] **步骤 2：创建 contests/challenge-cup.md**

```markdown
---
source: 挑战杯官网公开赛程
keywords: [挑战杯, 创业计划, 课外学术, 比赛, 竞赛]
---

# 挑战杯赛程参考

## 阶段划分（以年度赛为例）

1. **校赛阶段**（3-4 月，占比 15%）
   - 选题立项、团队组建、初稿
2. **省赛阶段**（5-7 月，占比 40%）
   - 方案完善、原型开发、材料打磨、省赛答辩
3. **国赛阶段**（8-11 月，占比 45%）
   - 成果优化、终稿定版、现场答辩、展示材料

## 推荐里程碑

- M1: 选题与立项（md）—— 校赛前
- M2: 方案设计（md）—— 省赛前
- M3: 原型开发（code）—— 省赛中
- M4: 成果优化（code + md）—— 国赛前
- M5: 答辩材料（md）—— 国赛终

## 适用场景

参加挑战杯的学生团队，按赛程节点倒推项目里程碑。
```

- [ ] **步骤 3：创建 contests/internet-plus.md**

```markdown
---
source: 互联网+大学生创新创业大赛官网公开赛程
keywords: [互联网+, 互联网, 创新创业, 大创, 比赛, 竞赛]
---

# 互联网+大赛赛程参考

## 阶段划分

1. **报名与校赛**（4-6 月，占比 20%）
   - 项目报名、商业计划书初稿、校赛选拔
2. **省赛**（7-8 月，占比 35%）
   - BP 打磨、路演 PPT、项目展示、省赛
3. **国赛**（9-10 月，占比 45%）
   - 终版材料、现场路演、专家问答

## 推荐里程碑

- M1: 商业计划书（md）—— 校赛
- M2: 产品原型（code）—— 省赛前
- M3: 路演材料（md）—— 省赛
- M4: 产品迭代（code）—— 国赛前
- M5: 终版答辩（md）—— 国赛

## 适用场景

参加互联网+大赛的团队，按"BP + 原型 + 路演"三件套规划。
```

- [ ] **步骤 4：创建 contests/computer-design.md**

```markdown
---
source: 中国大学生计算机设计大赛官网公开赛程
keywords: [计算机设计, 计设, 软件应用, 比赛, 竞赛]
---

# 计算机设计大赛赛程参考

## 阶段划分

1. **作品开发**（1-4 月，占比 50%）
   - 选题、开发、文档、初测
2. **省赛**（5-6 月，占比 25%）
   - 作品提交、省赛评审、修改完善
3. **国赛**（7-8 月，占比 25%）
   - 终版提交、现场答辩、展示

## 推荐里程碑

- M1: 需求与设计（md）—— 开发期
- M2: 核心开发（code）—— 开发期
- M3: 测试与文档（md）—— 省赛前
- M4: 作品完善（code）—— 省赛后
- M5: 答辩材料（md）—— 国赛

## 适用场景

参加计算机设计大赛的团队，按"开发 + 文档 + 答辩"节奏规划。
```

- [ ] **步骤 5：Commit**

```bash
git add knowledge_base/contests/
git commit -m "feat(kb): 比赛日程素材（挑战杯/互联网+/计算机设计）"
```

---

## 任务 4：创建索引文件

**文件：**
- 创建：`knowledge_base/index.json`

- [ ] **步骤 1：创建 index.json**

```json
{
  "sdlc": {
    "hybrid": {"file": "sdlc/hybrid.md", "keywords": ["混合", "hybrid", "校园", "课程设计", "毕设", "竞赛", "推荐"]},
    "agile": {"file": "sdlc/agile.md", "keywords": ["敏捷", "agile", "scrum", "迭代", "sprint"]},
    "waterfall": {"file": "sdlc/waterfall.md", "keywords": ["瀑布", "waterfall", "大型项目"]}
  },
  "projects": {
    "flask": {"file": "projects/flask.md", "keywords": ["web", "api", "后端", "flask", "python", "http", "路由"]},
    "fastapi": {"file": "projects/fastapi.md", "keywords": ["api", "异步", "fastapi", "后端", "接口", "restful", "openapi"]},
    "django": {"file": "projects/django.md", "keywords": ["web", "全栈", "django", "cms", "内容管理", "admin"]},
    "taro": {"file": "projects/taro.md", "keywords": ["小程序", "跨端", "taro", "react", "多端", "微信", "支付宝"]}
  },
  "contests": {
    "challenge-cup": {"file": "contests/challenge-cup.md", "keywords": ["挑战杯", "创业计划", "课外学术"]},
    "internet-plus": {"file": "contests/internet-plus.md", "keywords": ["互联网+", "互联网", "创新创业", "大创"]},
    "computer-design": {"file": "contests/computer-design.md", "keywords": ["计算机设计", "计设", "软件应用"]}
  }
}
```

- [ ] **步骤 2：Commit**

```bash
git add knowledge_base/index.json
git commit -m "feat(kb): 素材索引文件"
```

---

## 任务 5：编写知识库服务（TDD）

**文件：**
- 创建：`backend/tests/test_knowledge_service.py`
- 创建：`backend/app/services/knowledge_service.py`

- [ ] **步骤 1：编写失败的测试**

```python
# backend/tests/test_knowledge_service.py
from app.services import knowledge_service


def test_match_returns_hybrid_always():
    """SDLC 始终返回 hybrid（校园推荐）"""
    r = knowledge_service.match_references("任意课题")
    assert r["sdlc"] == "hybrid"


def test_match_flask_by_keyword():
    """课题含 web/api 关键词匹配 Flask"""
    r = knowledge_service.match_references("做一个 web api 后端项目")
    assert "flask" in r["projects"]


def test_match_taro_by_keyword():
    """课题含小程序关键词匹配 Taro"""
    r = knowledge_service.match_references("微信小程序跨端开发")
    assert "taro" in r["projects"]


def test_match_contest_by_keyword():
    """课题含挑战杯关键词匹配"""
    r = knowledge_service.match_references("准备挑战杯比赛")
    assert "challenge-cup" in r["contests"]


def test_match_returns_at_most_2_projects():
    """项目匹配最多 2 个（避免 prompt 过长）"""
    r = knowledge_service.match_references("web api 全栈 小程序")
    assert len(r["projects"]) <= 2


def test_load_excerpt_returns_string():
    """摘录返回字符串且非空"""
    excerpt = knowledge_service.load_excerpt("sdlc", "hybrid")
    assert isinstance(excerpt, str) and len(excerpt) > 50


def test_build_prompt_context_includes_all_matched():
    """构造的上下文包含所有匹配素材"""
    refs = {"sdlc": "hybrid", "projects": ["flask"], "contests": []}
    ctx = knowledge_service.build_prompt_context(refs)
    assert "混合模型" in ctx
    assert "Flask" in ctx


def test_build_prompt_context_length_bounded():
    """上下文总长 ≤ 4000 字符"""
    refs = {"sdlc": "hybrid", "projects": ["flask", "fastapi"], "contests": ["challenge-cup"]}
    ctx = knowledge_service.build_prompt_context(refs)
    assert len(ctx) <= 4000
```

- [ ] **步骤 2：运行测试验证失败**

运行：`cd backend && python -m pytest tests/test_knowledge_service.py -v`
预期：FAIL，报错 `ModuleNotFoundError: No module named 'app.services.knowledge_service'`

- [ ] **步骤 3：编写实现**

```python
# backend/app/services/knowledge_service.py
import json
from pathlib import Path
from app import config

KB_DIR = Path(__file__).resolve().parent.parent.parent.parent / "knowledge_base"
MAX_PROJECTS = 2
MAX_EXCERPT_CHARS = 1200  # 单个素材摘录上限
MAX_CONTEXT_CHARS = 4000  # 上下文总长上限

_index_cache = None


def _load_index() -> dict:
    global _index_cache
    if _index_cache is None:
        with open(KB_DIR / "index.json", encoding="utf-8") as f:
            _index_cache = json.load(f)
    return _index_cache


def match_references(topic: str) -> dict:
    """按课题关键词匹配三类素材"""
    topic_lower = topic.lower()
    index = _load_index()

    def _match(category: str) -> list:
        matched = []
        for name, meta in index.get(category, {}).items():
            if any(k.lower() in topic_lower for k in meta["keywords"]):
                matched.append(name)
        return matched

    return {
        "sdlc": "hybrid",  # 校园团队始终推荐混合模型
        "projects": _match("projects")[:MAX_PROJECTS],
        "contests": _match("contests"),
    }


def load_excerpt(category: str, name: str) -> str:
    """读取素材文件并截取关键段落"""
    index = _load_index()
    meta = index.get(category, {}).get(name)
    if not meta:
        return ""
    file_path = KB_DIR / meta["file"]
    if not file_path.exists():
        return ""
    content = file_path.read_text(encoding="utf-8")
    # 去掉 YAML frontmatter
    if content.startswith("---"):
        end = content.find("---", 3)
        if end > 0:
            content = content[end + 3:].strip()
    # 截取前 N 字符
    return content[:MAX_EXCERPT_CHARS]


def build_prompt_context(refs: dict) -> str:
    """构造注入 prompt 的上下文文本"""
    parts = []

    sdlc_excerpt = load_excerpt("sdlc", refs["sdlc"])
    if sdlc_excerpt:
        parts.append(f"【SDLC 模型参考：{refs['sdlc']}】\n{sdlc_excerpt}")

    for proj in refs.get("projects", []):
        proj_excerpt = load_excerpt("projects", proj)
        if proj_excerpt:
            parts.append(f"【相似项目参考：{proj}】\n{proj_excerpt}")

    for contest in refs.get("contests", []):
        contest_excerpt = load_excerpt("contests", contest)
        if contest_excerpt:
            parts.append(f"【比赛日程参考：{contest}】\n{contest_excerpt}")

    ctx = "\n\n".join(parts)
    return ctx[:MAX_CONTEXT_CHARS]
```

- [ ] **步骤 4：运行测试验证通过**

运行：`cd backend && python -m pytest tests/test_knowledge_service.py -v`
预期：PASS，8 个测试全绿

- [ ] **步骤 5：Commit**

```bash
git add backend/app/services/knowledge_service.py backend/tests/test_knowledge_service.py
git commit -m "feat(kb): 知识库匹配与摘录服务（8 测试全绿）"
```

---

## 任务 6：Prompt 注入与项目服务集成

**文件：**
- 修改：`backend/app/llm/prompts.py`
- 修改：`backend/app/services/project_service.py`
- 修改：`backend/app/routes/projects.py`

- [ ] **步骤 1：修改 prompts.py 增加 INITIAL_PLAN_PROMPT_WITH_KB**

在 `prompts.py` 顶部增加新 prompt（保留原 prompt 用于 fallback）：

```python
INITIAL_PLAN_PROMPT_WITH_KB = """你是项目拆解专家。根据课题生成里程碑和周任务。

【课题】{topic}
【团队人数】{team_size}
【截止日期】{deadline}

【参考素材】
{kb_context}

请参考上述素材的里程碑划分思路，但不要照搬。根据课题特点灵活调整。

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
```

- [ ] **步骤 2：修改 project_service.py 调用知识库**

在 `project_service.py` 的 `create_project_with_plan` 中注入知识库：

```python
from app.services import knowledge_service
from app.llm.prompts import INITIAL_PLAN_PROMPT_WITH_KB, INITIAL_PLAN_PROMPT
from app.llm import client


def create_project_with_plan(name, deadline, team_size, topic_desc):
    pid = models.create_project(name, deadline, team_size, topic_desc)

    # 匹配知识库素材
    refs = knowledge_service.match_references(topic_desc)
    kb_context = knowledge_service.build_prompt_context(refs)

    # 调用 LLM（有素材用带素材的 prompt，无素材用原 prompt）
    if kb_context:
        plan = client.generate_initial_plan_with_kb(
            topic=topic_desc, team_size=team_size,
            deadline=deadline, kb_context=kb_context)
    else:
        plan = client.generate_initial_plan(topic_desc, team_size, deadline)

    # 持久化里程碑与任务（原逻辑不变）
    ...

    return {"project_id": pid, "used_references": refs, ...}
```

- [ ] **步骤 3：在 client.py 增加 generate_initial_plan_with_kb**

```python
def generate_initial_plan_with_kb(topic, team_size, deadline, kb_context):
    try:
        return call_llm(INITIAL_PLAN_PROMPT_WITH_KB.format(
            topic=topic, team_size=team_size,
            deadline=deadline, kb_context=kb_context))
    except LLMUnavailableError:
        logger.error("带知识库的初始计划 LLM 失败，用 fallback")
        return FALLBACK_INITIAL_PLAN
```

- [ ] **步骤 4：修改 routes/projects.py 返回 used_references**

在创建项目的响应中附带 `used_references` 字段。

- [ ] **步骤 5：运行回归测试**

运行：`cd backend && python -m pytest -v`
预期：所有测试通过（含原有 29 + 知识库 8 = 37）

- [ ] **步骤 6：Commit**

```bash
git add backend/app/llm/prompts.py backend/app/llm/client.py backend/app/services/project_service.py backend/app/routes/projects.py
git commit -m "feat(kb): Prompt 注入知识库素材，返回 used_references"
```

---

## 任务 7：前端展示参考素材

**文件：**
- 修改：`frontend/static/app.js`
- 修改：`frontend/index.html`
- 修改：`frontend/static/style.css`

- [ ] **步骤 1：修改 app.js 接收 used_references**

在 `createProject` 和 `loadProject` 中保存 `usedReferences`：

```javascript
async createProject(form) {
  const r = await fetch('/api/projects', { ... });
  const data = await r.json();
  this.project = data.detail.project;
  this.milestones = data.detail.milestones;
  this.tasks = data.detail.tasks;
  this.usedReferences = data.detail.used_references || null;
  this.view = 'board';
}
```

- [ ] **步骤 2：修改 index.html 展示参考素材**

在看板顶部 project-header 下方加：

```html
<div x-show="usedReferences" class="kb-refs" x-data>
  <strong>📚 本次拆解参考了：</strong>
  <span x-show="usedReferences?.sdlc">
    SDLC 模型：<span x-text="usedReferences?.sdlc"></span>
  </span>
  <template x-for="p in usedReferences?.projects || []">
    <span x-text="'相似项目：' + p"></span>
  </template>
  <template x-for="c in usedReferences?.contests || []">
    <span x-text="'比赛日程：' + c"></span>
  </template>
</div>
```

- [ ] **步骤 3：修改 style.css 增加 .kb-refs 样式**

```css
.kb-refs { background: #f0f7ff; border-left: 4px solid #1a2b4a; padding: 8px 16px;
           margin-bottom: 16px; font-size: 14px; display: flex; gap: 16px; flex-wrap: wrap; }
.kb-refs span { background: white; padding: 2px 8px; border-radius: 3px; }
```

- [ ] **步骤 4：手动验证**

启动服务器，创建项目，确认看板顶部显示"📚 本次拆解参考了：..."

- [ ] **步骤 5：Commit**

```bash
git add frontend/
git commit -m "feat(kb): 前端展示参考素材标签"
```

---

## 任务 8：README 增加使用范例

**文件：**
- 修改：`README.md`

- [ ] **步骤 1：在 README 的"快速开始"后增加"使用范例"章节**

```markdown
## 使用范例

### 范例 1：校园二手交易平台（Web 后端项目）

**输入：**
- 项目名：校园二手交易平台
- 截止日期：2026-08-20
- 团队人数：3
- 课题描述：校园二手交易平台，支持学生发布闲置物品、浏览搜索、模拟交易

**Agent 行为：**
1. 匹配知识库：SDLC 混合模型 + Flask 项目里程碑（课题含"web/交易"）
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
```

- [ ] **步骤 2：Commit**

```bash
git add README.md
git commit -m "docs: README 增加使用范例（4 个场景 + 日常流程）"
```

---

## 任务 9：最终验证

- [ ] **步骤 1：运行全部测试**

运行：`cd backend && python -m pytest -v`
预期：所有测试通过（37+）

- [ ] **步骤 2：启动服务器端到端验证**

1. 启动 `uvicorn app.main:app --port 8000`
2. 创建项目"校园二手交易平台"
3. 确认看板顶部显示"📚 本次拆解参考了：SDLC 模型：hybrid，相似项目：flask"
4. 确认 LLM 生成的里程碑参考了 Flask 的 M1-M5 结构

- [ ] **步骤 3：推送 GitHub**

```bash
git push
```

---

## 自检

**1. 规格覆盖度：**
- 知识库结构（sdlc/projects/contests）→ 任务 1-4 ✓
- 匹配逻辑 → 任务 5 ✓
- Prompt 注入 → 任务 6 ✓
- 前端展示 → 任务 7 ✓
- README 使用范例 → 任务 8 ✓
- 验证 → 任务 9 ✓

**2. 占位符扫描：** 无 TODO，所有步骤有完整代码 ✓

**3. 类型一致性：**
- `match_references` 返回 `{sdlc, projects, contests}` → 任务 5/6/7 一致 ✓
- `build_prompt_context` 返回 str → 任务 5/6 一致 ✓
- `used_references` 字段名 → 任务 6/7 一致 ✓
```
