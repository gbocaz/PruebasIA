from datetime import timedelta

import pyotp
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.limiter import limiter
from app.models.user import RefreshToken, User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    TokenResponse,
    TwoFAConfirm,
    TwoFASetupOut,
    UserOut,
)
from app.security.audit import write_audit
from app.security.deps import get_current_user
from app.security.passwords import hash_password, verify_password
from app.security.rbac import client_ip
from app.security.tokens import create_access_token, new_token, sha256_hex, utcnow, as_utc

router = APIRouter(prefix="/api/auth", tags=["auth"])
REFRESH_COOKIE = "tic_refresh"


def _set_refresh_cookie(response: Response, raw_token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        REFRESH_COOKIE,
        raw_token,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        max_age=settings.refresh_token_days * 86400,
        path="/api/auth",
    )


def _issue_tokens(db: Session, user: User, request: Request, response: Response) -> TokenResponse:
    settings = get_settings()
    access = create_access_token(user.id, user.role, user.username)
    raw_refresh = new_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=sha256_hex(raw_refresh),
            expires_at=utcnow() + timedelta(days=settings.refresh_token_days),
            user_agent=request.headers.get("user-agent", "")[:255],
            ip_address=client_ip(request),
        )
    )
    _set_refresh_cookie(response, raw_refresh)
    return TokenResponse(
        access_token=access,
        expires_in=settings.access_token_minutes * 60,
        role=user.role,
        username=user.username,
    )


@router.post("/login", response_model=TokenResponse)
@limiter.limit(get_settings().rate_limit_login)
def login(request: Request, body: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == body.username).one_or_none()
    if user is None or not user.is_active or not verify_password(body.password, user.password_hash):
        write_audit(db, user=None, ip=client_ip(request), action="login", result="error", details="credenciales inválidas")
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuario o contraseña incorrectos")
    if user.totp_enabled:
        if not body.totp_code:
            return TokenResponse(access_token="", expires_in=0, requires_2fa=True, username=user.username, role=user.role)
        if not user.totp_secret or not pyotp.TOTP(user.totp_secret).verify(body.totp_code, valid_window=1):
            write_audit(db, user=user, ip=client_ip(request), action="login_2fa", result="error")
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Código 2FA inválido")
    user.last_login_at = utcnow()
    write_audit(db, user=user, ip=client_ip(request), action="login")
    return _issue_tokens(db, user, request, response)


@router.post("/refresh", response_model=TokenResponse)
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    raw = request.cookies.get(REFRESH_COOKIE)
    if not raw:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "No hay sesión")
    row = db.query(RefreshToken).filter(RefreshToken.token_hash == sha256_hex(raw)).one_or_none()
    if row is None or row.revoked_at is not None or as_utc(row.expires_at) < utcnow():
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh inválido")
    user = db.get(User, row.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuario no válido")
    row.revoked_at = utcnow()
    return _issue_tokens(db, user, request, response)


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    raw = request.cookies.get(REFRESH_COOKIE)
    if raw:
        row = db.query(RefreshToken).filter(RefreshToken.token_hash == sha256_hex(raw)).one_or_none()
        if row:
            row.revoked_at = utcnow()
    response.delete_cookie(REFRESH_COOKIE, path="/api/auth")
    write_audit(db, user=user, ip=client_ip(request), action="logout")
    return {"ok": True}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.post("/change-password")
def change_password(
    request: Request,
    body: ChangePasswordRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Contraseña actual incorrecta")
    user.password_hash = hash_password(body.new_password)
    write_audit(db, user=user, ip=client_ip(request), action="change_password")
    return {"ok": True}


@router.post("/2fa/setup", response_model=TwoFASetupOut)
def setup_2fa(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    secret = pyotp.random_base32()
    user.totp_secret = secret
    user.totp_enabled = False
    url = pyotp.totp.TOTP(secret).provisioning_uri(name=user.username, issuer_name="TIC Control AI")
    return TwoFASetupOut(secret=secret, otpauth_url=url)


@router.post("/2fa/enable")
def enable_2fa(
    request: Request,
    body: TwoFAConfirm,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not user.totp_secret or not pyotp.TOTP(user.totp_secret).verify(body.code, valid_window=1):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Código 2FA inválido")
    user.totp_enabled = True
    write_audit(db, user=user, ip=client_ip(request), action="enable_2fa")
    return {"ok": True}


@router.post("/2fa/disable")
def disable_2fa(
    request: Request,
    body: TwoFAConfirm,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not user.totp_enabled or not user.totp_secret:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "2FA no está activo")
    if not pyotp.TOTP(user.totp_secret).verify(body.code, valid_window=1):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Código 2FA inválido")
    user.totp_enabled = False
    user.totp_secret = None
    write_audit(db, user=user, ip=client_ip(request), action="disable_2fa")
    return {"ok": True}
