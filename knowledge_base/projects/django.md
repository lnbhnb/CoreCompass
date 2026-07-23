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
