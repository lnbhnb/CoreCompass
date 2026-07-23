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
