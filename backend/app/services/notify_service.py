import hashlib
import hmac
import base64
import time
import json
import logging
from datetime import datetime, timedelta
import httpx
from apscheduler.schedulers.background import BackgroundScheduler
from app import config, models

logger = logging.getLogger(__name__)
_scheduler: BackgroundScheduler = None


def _sign_feishu(secret: str):
    timestamp = str(int(time.time()))
    string_to_sign = f"{timestamp}\n{secret}"
    hmac_code = hmac.new(string_to_sign.encode("utf-8"), digestmod=hashlib.sha256).digest()
    return timestamp, base64.b64encode(hmac_code).decode("utf-8")


def send_feishu(text: str, project_id: int = None, msg_type: str = "manual_test") -> dict:
    if not config.FEISHU_WEBHOOK_URL:
        logger.warning("未配置 FEISHU_WEBHOOK_URL，跳过推送")
        result = {"status": "failed", "response": "webhook 未配置"}
        models.insert_notification(project_id, msg_type, text, "failed",
                                   json.dumps(result, ensure_ascii=False))
        return result
    payload = {"msg_type": "text", "content": {"text": text}}
    if config.FEISHU_SECRET:
        ts, sign = _sign_feishu(config.FEISHU_SECRET)
        payload["timestamp"] = ts
        payload["sign"] = sign
    try:
        resp = httpx.post(config.FEISHU_WEBHOOK_URL, json=payload, timeout=10)
        resp_data = resp.json()
        status = "sent" if resp.status_code == 200 and resp_data.get("StatusCode", 0) == 0 else "failed"
        result = {"status": status, "response": json.dumps(resp_data, ensure_ascii=False)}
    except Exception as e:
        logger.error(f"飞书推送失败: {e}")
        result = {"status": "failed", "response": str(e)}
    models.insert_notification(project_id, msg_type, text, result["status"],
                               result.get("response", ""))
    return result


def scan_and_notify_overdue():
    """定时扫描逾期任务并推送"""
    overdue = models.list_overdue_tasks()
    if not overdue:
        return {"scanned": 0, "notified": 0}
    by_project = {}
    for t in overdue:
        by_project.setdefault(t["project_id"], []).append(t)
    for pid, tasks in by_project.items():
        lines = [f"⚠️ 项目有 {len(tasks)} 个任务逾期："]
        for t in tasks[:5]:
            lines.append(f"· 《{t['title']}》状态={t['status']}")
        send_feishu("\n".join(lines), project_id=pid, msg_type="overdue")
    return {"scanned": len(overdue), "notified": len(by_project)}


def start_scheduler():
    global _scheduler
    if _scheduler is not None:
        return
    _scheduler = BackgroundScheduler()
    _scheduler.add_job(scan_and_notify_overdue, "interval",
                       minutes=config.SCHEDULER_INTERVAL_MINUTES, id="scan_overdue",
                       next_run_time=datetime.now() + timedelta(seconds=30))
    _scheduler.start()


def stop_scheduler():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None


def get_scheduler_status():
    """返回定时调度器状态：是否运行、间隔分钟、下次扫描时间。"""
    if _scheduler is None or not _scheduler.running:
        return {"running": False, "interval_minutes": config.SCHEDULER_INTERVAL_MINUTES,
                "next_run_at": None}
    job = _scheduler.get_job("scan_overdue") if _scheduler else None
    next_run = job.next_run_time.isoformat() if job and job.next_run_time else None
    return {"running": True, "interval_minutes": config.SCHEDULER_INTERVAL_MINUTES,
            "next_run_at": next_run}
