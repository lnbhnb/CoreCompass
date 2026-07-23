import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "corecompass.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

VOLC_AK = os.getenv("VOLC_AK", "")
VOLC_SK = os.getenv("VOLC_SK", "")
VOLC_MODEL = os.getenv("VOLC_MODEL", "doubao-pro-32k")
FEISHU_WEBHOOK_URL = os.getenv("FEISHU_WEBHOOK_URL", "")
FEISHU_SECRET = os.getenv("FEISHU_SECRET", "")
SCHEDULER_INTERVAL_MINUTES = int(os.getenv("SCHEDULER_INTERVAL_MINUTES", "1440"))
