from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.device import DeviceGroup
from app.models.user import EnrollmentToken, User
from app.schemas.ops import EnrollmentTokenCreate, EnrollmentTokenOut
from app.security.audit import write_audit
from app.security.deps import get_current_user
from app.security.rbac import ADMIN_ROLES, client_ip, require_roles
from app.security.tokens import new_token, sha256_hex, utcnow

router = APIRouter(prefix="/api/agents", tags=["agents-admin"])


@router.get("/enrollment-tokens", response_model=list[EnrollmentTokenOut])
def list_tokens(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_roles(user, ADMIN_ROLES)
    rows = db.query(EnrollmentToken).order_by(EnrollmentToken.created_at.desc()).all()
    return [
        EnrollmentTokenOut(
            id=r.id,
            label=r.label,
            token_prefix=r.token_prefix,
            max_uses=r.max_uses,
            use_count=r.use_count,
            expires_at=r.expires_at,
            group_id=r.group_id,
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.post("/enrollment-tokens", response_model=EnrollmentTokenOut, status_code=201)
def create_token(
    request: Request,
    body: EnrollmentTokenCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_roles(user, ADMIN_ROLES)
    if body.group_id and db.get(DeviceGroup, body.group_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Grupo no encontrado")
    raw = new_token(24)
    expires = utcnow() + timedelta(hours=body.expires_hours) if body.expires_hours else None
    row = EnrollmentToken(
        label=body.label,
        token_hash=sha256_hex(raw),
        token_prefix=raw[:8],
        max_uses=body.max_uses,
        expires_at=expires,
        group_id=body.group_id,
        created_by=user.id,
    )
    db.add(row)
    db.flush()
    write_audit(db, user=user, ip=client_ip(request), action="enrollment_token_create", target_type="enrollment_token", target_id=row.id)
    return EnrollmentTokenOut(
        id=row.id,
        label=row.label,
        token=raw,
        token_prefix=row.token_prefix,
        max_uses=row.max_uses,
        use_count=0,
        expires_at=row.expires_at,
        group_id=row.group_id,
        created_at=row.created_at,
    )


@router.post("/enrollment-tokens/{token_id}/revoke")
def revoke_token(
    token_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_roles(user, ADMIN_ROLES)
    row = db.get(EnrollmentToken, token_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Token no encontrado")
    row.revoked_at = utcnow()
    write_audit(db, user=user, ip=client_ip(request), action="enrollment_token_revoke", target_type="enrollment_token", target_id=row.id)
    return {"ok": True}
