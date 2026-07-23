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
