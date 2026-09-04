from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.ops import Alert
from app.models.user import User
from app.schemas.ops import AlertOut
from app.security.audit import write_audit
from app.security.deps import get_current_user
from app.security.rbac import READ_ROLES, SUPPORT_ACTIONS, client_ip, require_roles
from app.security.tokens import utcnow

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertOut])
def list_alerts(
    acknowledged: bool | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_roles(user, READ_ROLES)
    query = db.query(Alert)
    if acknowledged is not None:
        query = query.filter(Alert.acknowledged.is_(acknowledged))
    return query.order_by(Alert.created_at.desc()).limit(300).all()


@router.post("/{alert_id}/ack")
def ack_alert(
    alert_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_roles(user, SUPPORT_ACTIONS)
    row = db.get(Alert, alert_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Alerta no encontrada")
    row.acknowledged = True
    row.acknowledged_by = user.id
    row.acknowledged_at = utcnow()
    write_audit(db, user=user, ip=client_ip(request), action="alert_ack", target_type="alert", target_id=row.id)
    return {"ok": True}
