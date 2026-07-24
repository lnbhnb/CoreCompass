import hashlib
import secrets
from datetime import datetime, timedelta
from app import models, db


TOKEN_TTL_DAYS = 7


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
    return salt.hex() + ":" + dk.hex()


def _verify_password(password: str, stored: str) -> bool:
    salt_hex, dk_hex = stored.split(":")
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), 100000)
    return secrets.compare_digest(dk.hex(), dk_hex)


def _issue_token(conn, user_id: int) -> str:
    """生成新 token 并写入 DB，同时设置过期时间。"""
    token = secrets.token_hex(32)
    expires_at = (datetime.now() + timedelta(days=TOKEN_TTL_DAYS)).isoformat()
    conn.execute(
        "UPDATE users SET token=?, token_expires_at=? WHERE id=?",
        (token, expires_at, user_id))
    return token


def register(username, password, display_name):
    if models.get_user_by_username(username):
        raise ValueError("用户名已存在")
    password_hash = _hash_password(password)
    token = secrets.token_hex(32)
    expires_at = (datetime.now() + timedelta(days=TOKEN_TTL_DAYS)).isoformat()
    uid = models.create_user(username, password_hash, display_name, token, expires_at)
    return {"user": {"id": uid, "username": username, "display_name": display_name}, "token": token}


def login(username, password):
    user = models.get_user_by_username(username)
    if not user or not _verify_password(password, user["password_hash"]):
        raise ValueError("用户名或密码错误")
    token = secrets.token_hex(32)
    expires_at = (datetime.now() + timedelta(days=TOKEN_TTL_DAYS)).isoformat()
    with db.get_conn() as conn:
        conn.execute(
            "UPDATE users SET token=?, token_expires_at=? WHERE id=?",
            (token, expires_at, user["id"]))
    return {"user": {"id": user["id"], "username": user["username"], "display_name": user["display_name"]}, "token": token}


def logout(token):
    user = models.get_user_by_token(token)
    if user:
        models.clear_user_token(user["id"])


def get_user_by_token(token):
    user = models.get_user_by_token(token)
    if not user:
        return None
    # token 过期校验
    expires_at = user.get("token_expires_at")
    if expires_at and datetime.fromisoformat(expires_at) < datetime.now():
        models.clear_user_token(user["id"])
        return None
    return {"id": user["id"], "username": user["username"], "display_name": user["display_name"]}
