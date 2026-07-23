from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from app.services import auth_service, member_service
from app import deps

router = APIRouter()


class RegisterReq(BaseModel):
    username: str
    password: str
    display_name: str


class LoginReq(BaseModel):
    username: str
    password: str


class JoinReq(BaseModel):
    invite_code: str


def _extract_token(authorization: str | None) -> str | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    return authorization[7:]


@router.post("/api/auth/register")
def register(req: RegisterReq):
    try:
        return auth_service.register(req.username, req.password, req.display_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/auth/login")
def login(req: LoginReq):
    try:
        return auth_service.login(req.username, req.password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/auth/logout")
def logout(authorization: str | None = Header(None)):
    token = _extract_token(authorization)
    if token:
        auth_service.logout(token)
    return {"ok": True}


@router.post("/api/auth/join")
def join(req: JoinReq, authorization: str | None = Header(None)):
    token = _extract_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="未登录")
    try:
        return member_service.join_with_code(req.invite_code, token)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/api/auth/me")
def me(authorization: str | None = Header(None)):
    token = _extract_token(authorization)
    return deps.get_current_user(token)
