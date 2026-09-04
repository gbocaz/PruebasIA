from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.enums import DeviceStatus, SoftwareCategory
from app.models.device import Device
from app.models.ops import Alert
from app.models.software import DeviceSoftware, InstallJobDevice, Software
from app.models.user import User
from app.security.deps import get_current_user
from app.security.rbac import READ_ROLES, require_roles

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("")
def dashboard(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_roles(user, READ_ROLES)
    devices = db.query(Device).all()
    total = len(devices)
    online = sum(1 for d in devices if d.status == DeviceStatus.ONLINE.value)
    offline = sum(1 for d in devices if d.status == DeviceStatus.OFFLINE.value)
    warning = sum(1 for d in devices if d.status in {DeviceStatus.ADVERTENCIA.value, DeviceStatus.CRITICO.value})
    open_alerts = db.query(Alert).filter(Alert.acknowledged.is_(False)).count()
    programs = db.query(func.count(Software.id)).scalar() or 0
    top_cpu = sorted(devices, key=lambda d: d.cpu_percent, reverse=True)[:8]
    top_software = (
        db.query(Software.name, func.count(DeviceSoftware.id))
        .join(DeviceSoftware, DeviceSoftware.software_id == Software.id)
        .group_by(Software.name)
        .order_by(func.count(DeviceSoftware.id).desc())
        .limit(8)
        .all()
    )
    recent_alerts = (
        db.query(Alert).order_by(Alert.created_at.desc()).limit(8).all()
    )
    unauthorized = (
        db.query(func.count(DeviceSoftware.id))
        .join(Software, Software.id == DeviceSoftware.software_id)
        .filter(Software.category == SoftwareCategory.NO_AUTORIZADO.value)
        .scalar()
        or 0
    )
    pending_installs = (
        db.query(func.count(InstallJobDevice.id))
        .filter(InstallJobDevice.status.in_(["pendiente", "descargando", "instalando"]))
        .scalar()
        or 0
    )
    available_pct = round((online / total) * 100, 1) if total else 0.0
    return {
        "totals": {
            "devices": total,
            "online": online,
            "offline": offline,
            "warning": warning,
            "alerts": open_alerts,
            "programs": programs,
            "unauthorized_installs": unauthorized,
            "pending_installs": pending_installs,
            "available_pct": available_pct,
        },
        "top_cpu": [
            {
                "id": d.id,
                "hostname": d.hostname,
                "cpu_percent": d.cpu_percent,
                "ram_used_mb": d.ram_used_mb,
                "ram_total_mb": d.ram_total_mb,
                "disk_used_gb": d.disk_used_gb,
                "disk_total_gb": d.disk_total_gb,
                "status": d.status,
            }
            for d in top_cpu
        ],
        "top_software": [{"name": n, "count": int(c)} for n, c in top_software],
        "recent_alerts": [
            {"id": a.id, "level": a.level, "title": a.title, "created_at": a.created_at, "acknowledged": a.acknowledged}
            for a in recent_alerts
        ],
    }
