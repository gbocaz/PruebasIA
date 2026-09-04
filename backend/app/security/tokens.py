import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import jwt

from app.config import get_settings


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def canonical_iso(dt: datetime) -> str:
    dt = as_utc(dt) or utcnow()
    dt = dt.replace(microsecond=0)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def new_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)


def create_access_token(user_id: str, role: str, username: str) -> str:
    settings = get_settings()
    payload = {
        "sub": user_id,
        "role": role,
        "username": username,
        "typ": "access",
        "exp": utcnow() + timedelta(minutes=settings.access_token_minutes),
        "iat": utcnow(),
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    settings = get_settings()
    return jwt.decode(token, settings.secret_key, algorithms=["HS256"])


def sign_task(hmac_secret: str, task_id: str, device_id: str, task_type: str, expires_iso: str) -> str:
    msg = f"{task_id}|{device_id}|{task_type}|{expires_iso}".encode("utf-8")
    return hmac.new(hmac_secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()
