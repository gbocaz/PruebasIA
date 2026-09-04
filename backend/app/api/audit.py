from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.ops import AuditLog
from app.models.user import User
from app.schemas.ops import AuditOut
from app.security.deps import get_current_user
from app.security.rbac import AUDIT_ROLES, require_roles

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("", response_model=list[AuditOut])
def list_audit(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_roles(user, AUDIT_ROLES)
    return db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(500).all()
