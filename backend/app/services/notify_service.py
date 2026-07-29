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

# 逾期天数 → (notify_level, 冷却分钟)
# 规则：刚逾期温和提醒、中度逾期加紧、严重逾期高频催促
COOLDOWN_RULES = [
    (1,    "normal",   360),   # ≤1天 → 每6小时
    (3,    "warning",  120),   # 2-3天 → 每2小时
    (None, "critical", 30),    # ≥4天 → 每30分钟
]

LEVEL_RANK = {"normal": 0, "warning": 1, "critical": 2}


def _days_overdue(due_date_str: str) -> int:
    """计算已逾期天数。0=今日截止，负值=还未逾期。"""
    if not due_date_str:
        return 0
    try:
        due = datetime.strptime(due_date_str[:10], "%Y-%m-%d")
        return (datetime.now().date() - due.date()).days
    except (ValueError, TypeError):
        return 0


def _get_notify_level(days: int) -> str:
    for max_days, level, _ in COOLDOWN_RULES:
        if max_days is None or days <= max_days:
            return level
    return "critical"


def _get_cooldown_minutes(days: int) -> int:
    for max_days, _, cooldown in COOLDOWN_RULES:
        if max_days is None or days <= max_days:
            return cooldown
    return 30


def _last_overdue_notify(project_id: int) -> dict | None:
    """项目最近一次 overdue 通知。"""
    with models.db.get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM notifications WHERE project_id=? AND type='overdue' "
            "ORDER BY created_at DESC LIMIT 1",
            (project_id,)).fetchone()
        return dict(row) if row else None


def _in_cooldown(project_id: int, level: str, cooldown_minutes: int) -> bool:
    """该级别通知是否在冷却期内。同级别或更高级别才计入冷却。"""
    last = _last_overdue_notify(project_id)
    if not last:
        return False
    last_level = last.get("notify_level", "normal")
    if LEVEL_RANK.get(last_level, 0) < LEVEL_RANK.get(level, 0):
        return False  # 上次级别更低，允许升级推送
    try:
        last_at = datetime.strptime(last["created_at"], "%Y-%m-%d %H:%M:%S")
        elapsed = (datetime.now() - last_at).total_seconds() / 60
        return elapsed < cooldown_minutes
    except (ValueError, TypeError):
        return False


def _sign_feishu(secret: str):
    timestamp = str(int(time.time()))
    string_to_sign = f"{timestamp}\n{secret}"
    hmac_code = hmac.new(string_to_sign.encode("utf-8"), digestmod=hashlib.sha256).digest()
    return timestamp, base64.b64encode(hmac_code).decode("utf-8")


def send_feishu(text: str, project_id: int = None, msg_type: str = "manual_test",
                notify_level: str = "normal") -> dict:
    webhook_url = config.FEISHU_WEBHOOK_URL
    secret = config.FEISHU_SECRET
    if project_id:
        project = models.get_project(project_id)
        if project:
            if project.get("feishu_webhook_url"):
                webhook_url = project["feishu_webhook_url"]
            if project.get("feishu_secret"):
                secret = project["feishu_secret"]

    if not webhook_url:
        logger.warning("未配置 FEISHU_WEBHOOK_URL，跳过推送")
        result = {"status": "failed", "response": "webhook 未配置"}
        models.insert_notification(project_id, msg_type, text, "failed",
                                   json.dumps(result, ensure_ascii=False),
                                   notify_level=notify_level)
        return result
    payload = {"msg_type": "text", "content": {"text": text}}
    if secret:
        ts, sign = _sign_feishu(secret)
        payload["timestamp"] = ts
        payload["sign"] = sign
    try:
        resp = httpx.post(webhook_url, json=payload, timeout=10)
        resp_data = resp.json()
        status = "sent" if resp.status_code == 200 and resp_data.get("StatusCode", 0) == 0 else "failed"
        result = {"status": status, "response": json.dumps(resp_data, ensure_ascii=False)}
    except Exception as e:
        logger.error(f"飞书推送失败: {e}")
        result = {"status": "failed", "response": str(e)}
    models.insert_notification(project_id, msg_type, text, result["status"],
                               result.get("response", ""),
                               notify_level=notify_level)
    return result


def _build_overdue_message(tasks: list, project_name: str, next_scan_at: str = "") -> str:
    """构建逾期通知消息，每项显示负责人 + deadline + 已逾期天数。"""
    now = datetime.now().strftime("%m-%d %H:%M")
    lines = [f"🔔 CoreCompass 进度巡检 · {now}", f"项目「{project_name}」", ""]
    for t in tasks:
        due_str = t.get("due_date", "")
        due_str = due_str[:10] if due_str else "未设定"
        days = _days_overdue(t.get("due_date"))
        if days > 0:
            days_str = f"已逾期 {days} 天"
        elif days == 0:
            days_str = "今日截止"
        else:
            days_str = f"还有 {-days} 天到期"
        assignee = t.get("assignee_name") or "未分配"
        lines.append(f"· {t['title']}")
        lines.append(f"  负责人：{assignee} | 截止 {due_str} | {days_str}")
    lines.append("")
    lines.append("💡 建议前往看板触发「重规划」调整计划")
    if next_scan_at:
        lines.append(f"📋 下次巡检：{next_scan_at}")
    return "\n".join(lines)


def scan_and_notify_overdue(forced: bool = False):
    """扫描逾期任务并推送飞书通知。

    forced=True（手动触发 / 即时触发）跳过冷却检查，始终推送。
    forced=False（定时扫描）受分级冷却约束。
    """
    overdue = models.list_overdue_tasks()
    if not overdue:
        return {"scanned": 0, "notified": 0}

    by_project = {}
    for t in overdue:
        by_project.setdefault(t["project_id"], []).append(t)

    notified_count = 0
    skipped_count = 0
    for pid, tasks in by_project.items():
        max_days = max(_days_overdue(t.get("due_date")) for t in tasks)
        level = _get_notify_level(max_days)
        cooldown = _get_cooldown_minutes(max_days)

        if not forced and _in_cooldown(pid, level, cooldown):
            skipped_count += 1
            continue

        project_name = tasks[0].get("project_name", f"项目#{pid}")
        next_scan = ""
        if _scheduler and _scheduler.running:
            job = _scheduler.get_job("scan_overdue")
            if job and job.next_run_time:
                next_scan = job.next_run_time.strftime("%m-%d %H:%M")

        text = _build_overdue_message(tasks, project_name, next_scan)
        send_feishu(text, project_id=pid, msg_type="overdue", notify_level=level)
        notified_count += 1

    return {"scanned": len(overdue), "notified": notified_count, "skipped": skipped_count}


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
    if _scheduler is None or not _scheduler.running:
        return {"running": False, "interval_minutes": config.SCHEDULER_INTERVAL_MINUTES,
                "next_run_at": None}
    job = _scheduler.get_job("scan_overdue") if _scheduler else None
    next_run = job.next_run_time.isoformat() if job and job.next_run_time else None
    return {"running": True, "interval_minutes": config.SCHEDULER_INTERVAL_MINUTES,
            "next_run_at": next_run}
