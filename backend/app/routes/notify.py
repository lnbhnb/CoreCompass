from fastapi import APIRouter, Header, HTTPException
from app.services import notify_service
from app import models, deps

router = APIRouter()


def _token(authorization: str | None):
    if not authorization or not authorization.startswith("Bearer "):
        return None
    return authorization[7:]


def _resolve_project_id(project_id) -> int | None:
    """容错解析 project_id：空字符串/None/0 视为未传。"""
    if project_id is None or project_id == "":
        return None
    try:
        pid = int(project_id)
        return pid if pid > 0 else None
    except (TypeError, ValueError):
        return None


@router.post("/api/notify/test")
def test_notify(project_id=None, authorization: str | None = Header(None)):
    """手动推送测试消息（Demo 主路径）。project_id 容错接受空字符串。"""
    token = _token(authorization)
    user = deps.get_current_user(token)
    pid = _resolve_project_id(project_id)
    if pid:
        deps.require_member(pid, user)
    text = f"【CoreCompass 测试通知】项目 ID={pid or 'N/A'} 的 Agent 正在主动联系你，请关注任务进度。"
    return notify_service.send_feishu(text, project_id=pid, msg_type="manual_test")


@router.post("/api/notify/scan")
def manual_scan(authorization: str | None = Header(None)):
    """手动触发逾期扫描（需要登录）。"""
    deps.get_current_user(_token(authorization))
    return notify_service.scan_and_notify_overdue()


@router.get("/api/notify/scheduler/status")
def scheduler_status(authorization: str | None = Header(None)):
    """获取定时调度器状态（下次扫描时间）。"""
    deps.get_current_user(_token(authorization))
    return notify_service.get_scheduler_status()


@router.get("/api/notifications")
def list_notifications(project_id=None, limit: int = 50, authorization: str | None = Header(None)):
    """列出通知日志。传 project_id 时按项目隔离。"""
    deps.get_current_user(_token(authorization))
    pid = _resolve_project_id(project_id)
    return models.list_notifications(pid, limit)
