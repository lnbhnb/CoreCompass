# CoreCompass

校园项目"伪需求"粉碎机。

## 启动

1. 复制 `backend/.env.example` 为 `backend/.env`，填火山引擎凭证和飞书 webhook
2. `pip install -r backend/requirements.txt`
3. `cd backend && uvicorn app.main:app --reload`
4. 浏览器打开 http://localhost:8000

## 测试

`cd backend && pytest -v`
