# 知识库设计文档（方案 A · 结构化素材 + Prompt 注入）

## 背景

当前 LLM 拆解是纯指令式 prompt，没有真实素材支撑。参赛要求中提到"使用开源社区中成熟项目的 Git 提交历史、标准的软件工程开发生命周期（SDLC）文档、以及真实的比赛日程规划模板作为知识库"。本设计在不引入向量数据库的前提下，通过结构化素材 + 关键词检索 + Prompt 注入，让 LLM 拆解"有据可依"，同时为评委提供可视的知识库目录。

## 目标

1. **LLM 拆解质量提升** —— 通过 few-shot 例子让拆解更贴合真实项目
2. **评委可视** —— `knowledge_base/` 目录有真实素材，Demo 时可展示
3. **可追溯** —— 拆解日志记录"参考了哪些素材"
4. **不破坏现有架构** —— 只在 prompt 构造处加一层

## 不做（YAGNI）

- 不做向量数据库 / embedding（知识库小，收益低）
- 不做自动爬取 GitHub（手动整理高质量素材即可）
- 不做多语言素材（仅中文项目）

## 架构

```
项目创建请求
    ↓
knowledge_service.match_references(topic)  ← 关键词匹配
    ↓
返回 [sdlc_refs, project_refs, contest_refs]
    ↓
project_service 构造 prompt（注入素材摘录）
    ↓
LLM 生成拆解
    ↓
拆解结果附带 used_references 字段
```

## 知识库结构

```
knowledge_base/
├── sdlc/                          # 软件工程生命周期模板
│   ├── README.md                  # 目录说明 + 引用规范
│   ├── waterfall.md               # 瀑布模型阶段定义
│   ├── agile.md                   # 敏捷迭代模型
│   └── hybrid.md                  # 校园团队推荐：混合模型
├── projects/                      # 真实开源项目里程碑数据
│   ├── README.md
│   ├── flask.md                   # Flask 项目里程碑（取自 GitHub milestones）
│   ├── fastapi.md                 # FastAPI 项目里程碑
│   ├── django.md                  # Django 项目里程碑
│   └── taro.md                    # Taro 跨端框架里程碑
├── contests/                      # 比赛日程模板
│   ├── README.md
│   ├── challenge-cup.md           # 挑战杯日程
│   ├── internet-plus.md           # 互联网+日程
│   └── computer-design.md         # 计算机设计大赛日程
└── index.json                     # 素材索引（关键词 → 文件路径 + 摘录）
```

## 素材内容规范

每个素材文件包含：
- `source`：来源（GitHub URL / 标准文档名）
- `keywords`：触发关键词列表
- `milestones`：里程碑结构化数据（名称 / 周期 / 关键产物）
- `notes`：适用场景说明

**示例（projects/flask.md）：**
```markdown
---
source: https://github.com/pallets/flask/milestones
keywords: [web, api, 后端, flask, python, http]
---

# Flask 项目里程碑参考

## M1: 基础架构（1 周）
- 关键产物：项目骨架、路由系统、配置管理
- 核心任务：初始化仓库、定义路由、配置加载

## M2: 核心功能（2 周）
- 关键产物：请求处理、响应渲染、模板引擎
...

## 适用场景
适合 Python Web 后端项目，尤其是中小型 API 服务。
```

## 检索逻辑（关键词匹配）

```python
def match_references(topic: str) -> dict:
    """
    返回三类素材的匹配结果：
    {
      "sdlc": "hybrid",           # 始终返回推荐模型
      "projects": ["flask"],      # 按课题关键词匹配
      "contests": []              # 可选，暂不强制
    }
    """
    topic_lower = topic.lower()
    matched_projects = []
    for proj_name, keywords in PROJECT_KEYWORDS.items():
        if any(k in topic_lower for k in keywords):
            matched_projects.append(proj_name)
    return {
        "sdlc": "hybrid",
        "projects": matched_projects[:2],  # 最多 2 个，避免 prompt 过长
        "contests": []
    }
```

## Prompt 注入

修改 `INITIAL_PLAN_PROMPT`，在指令后追加素材摘录：

```
你是项目拆解专家。根据课题生成里程碑和周任务。

【课题】{topic}
【团队人数】{team_size}
【截止日期】{deadline}

【参考素材】
- 软件工程生命周期模型：{sdlc_excerpt}
- 相似开源项目里程碑：{project_excerpt}

请参考上述素材的里程碑划分思路，但不要照搬。根据课题特点灵活调整。

输出严格 JSON：...
```

## 数据流变更

1. `project_service.create_project_with_plan()` 调用 `knowledge_service.match_references(topic)`
2. 读取匹配到的素材文件，截取关键段落（每个素材 ≤500 字）
3. 注入到 `INITIAL_PLAN_PROMPT`
4. 调用 LLM
5. 返回结果中附带 `used_references` 字段（前端可展示）

## 前端展示

在创建项目成功后，看板顶部显示：
```
📚 本次拆解参考了：
  · 软件工程生命周期：混合模型（适合校园团队）
  · 相似项目：Flask、FastAPI
```

## 测试

1. **素材完整性** —— 所有素材文件有 source / keywords / milestones 字段
2. **匹配逻辑** —— 关键词匹配返回正确结果
3. **Prompt 注入** —— 注入后 prompt 长度 ≤ 4000 字符
4. **回归** —— 现有 29 测试全绿

## 文件清单（新增）

```
knowledge_base/
├── sdlc/README.md, waterfall.md, agile.md, hybrid.md
├── projects/README.md, flask.md, fastapi.md, django.md, taro.md
├── contests/README.md, challenge-cup.md, internet-plus.md, computer-design.md
└── index.json
backend/app/services/knowledge_service.py
backend/tests/test_knowledge_service.py
```

## 工作量预估

- 素材整理：8-10 个 markdown 文件（真实数据，约 1.5 小时）
- knowledge_service.py：约 80 行（1 小时）
- prompt 修改 + 前端展示：约 30 分钟
- 测试：约 30 分钟
- **合计：约 3.5 小时**
