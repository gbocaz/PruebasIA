from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.device import Device
from app.models.software import Software
from app.models.user import User
from app.security.deps import get_current_user
from app.security.rbac import READ_ROLES, require_roles

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("")
def global_search(q: str = Query(min_length=1, max_length=128), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_roles(user, READ_ROLES)
    like = f"%{q}%"
    devices = (
        db.query(Device)
        .filter(
            Device.hostname.ilike(like)
            | Device.ip_address.ilike(like)
            | Device.mac_address.ilike(like)
            | Device.logged_user.ilike(like)
            | Device.display_name.ilike(like)
        )
        .limit(20)
        .all()
    )
    software = db.query(Software).filter(Software.name.ilike(like) | Software.publisher.ilike(like)).limit(20).all()
    return {
        "devices": [
            {"id": d.id, "hostname": d.hostname, "ip_address": d.ip_address, "mac_address": d.mac_address, "status": d.status}
            for d in devices
        ],
        "software": [{"id": s.id, "name": s.name, "publisher": s.publisher, "category": s.category} for s in software],
    }
