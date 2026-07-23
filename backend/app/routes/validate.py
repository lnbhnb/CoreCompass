from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services import validate_service

router = APIRouter()


@router.post("/api/validate/{milestone_id}")
async def validate(milestone_id: int, file: UploadFile = File(...)):
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件超过 10MB")
    return await validate_service.validate_milestone_artifact(milestone_id, file.filename, content)
