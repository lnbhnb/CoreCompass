import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "corecompass.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# LLM 配置（兼容 DeepSeek / 豆包 / 任何 OpenAI 协议模型）
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
LLM_MODEL = os.getenv("VOLC_MODEL", "deepseek-chat")  # 复用此变量作为模型名

# 兼容旧字段（保留但不再使用）
VOLC_AK = os.getenv("VOLC_AK", "")
VOLC_SK = os.getenv("VOLC_SK", "")
VOLC_MODEL = LLM_MODEL

FEISHU_WEBHOOK_URL = os.getenv("FEISHU_WEBHOOK_URL", "")
FEISHU_SECRET = os.getenv("FEISHU_SECRET", "")
SCHEDULER_INTERVAL_MINUTES = int(os.getenv("SCHEDULER_INTERVAL_MINUTES", "5"))
