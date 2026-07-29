FROM python:3.12-slim

WORKDIR /app

# 安装依赖（先复制 requirements 利用 Docker 缓存层）
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY knowledge_base/ ./knowledge_base/

# 工作目录设为 backend，uvicorn 在这里启动，load_dotenv() 也能找到 .env
WORKDIR /app/backend

# 创建 data 目录（SQLite + 上传文件）
RUN mkdir -p data

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
