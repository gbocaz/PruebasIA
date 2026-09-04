from sqlalchemy.orm import Session

from app.models.ops import AuditLog
from app.models.user import User


def write_audit(
    db: Session,
    *,
    user: User | None,
    ip: str,
    action: str,
    target_type: str = "",
    target_id: str = "",
    result: str = "ok",
    details: str = "",
) -> None:
    db.add(
        AuditLog(
            user_id=user.id if user else None,
            username=user.username if user else "",
            ip_address=ip,
            action=action,
            target_type=target_type,
            target_id=target_id,
            result=result,
            details=details[:4000],
        )
    )
