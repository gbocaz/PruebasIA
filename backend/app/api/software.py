from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.device import Device
from app.models.software import DeviceSoftware, Software
from app.models.user import User
from app.schemas.ops import SoftwareOut, SoftwareUpdate
from app.security.audit import write_audit
from app.security.deps import get_current_user
from app.security.rbac import ADMIN_ROLES, READ_ROLES, client_ip, require_roles
from fastapi import HTTPException, Request, status

router = APIRouter(prefix="/api/software", tags=["software"])


@router.get("", response_model=list[SoftwareOut])
def list_software(
    q: str | None = None,
    category: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_roles(user, READ_ROLES)
    counts = (
        db.query(DeviceSoftware.software_id, func.count(DeviceSoftware.id).label("c"))
        .group_by(DeviceSoftware.software_id)
        .subquery()
    )
    query = db.query(Software, func.coalesce(counts.c.c, 0)).outerjoin(counts, counts.c.software_id == Software.id)
    if q:
        like = f"%{q}%"
        query = query.filter(Software.name.ilike(like) | Software.publisher.ilike(like))
    if category:
        query = query.filter(Software.category == category)
    rows = query.order_by(Software.name).all()
    return [
        SoftwareOut(id=s.id, name=s.name, publisher=s.publisher, category=s.category, install_count=int(c))
        for s, c in rows
    ]


@router.patch("/{software_id}", response_model=SoftwareOut)
def update_software(
    software_id: str,
    request: Request,
    body: SoftwareUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_roles(user, ADMIN_ROLES)
    row = db.get(Software, software_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Software no encontrado")
    row.category = body.category.value
    write_audit(db, user=user, ip=client_ip(request), action="software_category", target_type="software", target_id=row.id, details=row.category)
    count = db.query(DeviceSoftware).filter(DeviceSoftware.software_id == row.id).count()
    return SoftwareOut(id=row.id, name=row.name, publisher=row.publisher, category=row.category, install_count=count)


@router.get("/search")
def search_software_presence(
    name: str = Query(min_length=1),
    missing: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """¿En cuántos equipos está X? ¿Qué equipos no lo tienen?"""
    require_roles(user, READ_ROLES)
    like = f"%{name}%"
    matches = db.query(Software).filter(Software.name.ilike(like)).all()
    software_ids = [s.id for s in matches]
    device_ids = set()
    if software_ids:
        rows = db.query(DeviceSoftware.device_id).filter(DeviceSoftware.software_id.in_(software_ids)).all()
        device_ids = {r[0] for r in rows}
    if missing:
        devices = db.query(Device).filter(~Device.id.in_(device_ids) if device_ids else True).order_by(Device.hostname).all()
    else:
        devices = db.query(Device).filter(Device.id.in_(device_ids)).order_by(Device.hostname).all() if device_ids else []
    return {
        "query": name,
        "missing": missing,
        "software_matches": [{"id": s.id, "name": s.name, "publisher": s.publisher} for s in matches],
        "device_count": len(devices),
        "devices": [{"id": d.id, "hostname": d.hostname, "status": d.status} for d in devices],
    }
