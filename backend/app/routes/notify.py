from fastapi import APIRouter
from app.services import notify_service
from app import models

router = APIRouter()


@router.post("/api/notify/test")
def test_notify(project_id: int = None):
    """手动推送测试消息（Demo 主路径）"""
    text = f"【CoreCompass 测试通知】项目 ID={project_id} 的 Agent 正在主动联系你，请关注任务进度。"
    return notify_service.send_feishu(text, project_id=project_id, msg_type="manual_test")


@router.post("/api/notify/scan")
def manual_scan():
    return notify_service.scan_and_notify_overdue()


@router.get("/api/notifications")
def list_notifications(project_id: int = None, limit: int = 50):
    return models.list_notifications(project_id, limit)
