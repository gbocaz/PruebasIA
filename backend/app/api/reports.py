from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from io import StringIO
import csv

from app.database import get_db
from app.models.device import Device
from app.models.user import User
from app.security.deps import get_current_user
from app.security.rbac import READ_ROLES, require_roles

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/inventory.csv")
def inventory_csv(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_roles(user, READ_ROLES)
    buf = StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "hostname",
            "estado",
            "so",
            "version",
            "ip",
            "mac",
            "usuario",
            "cpu_pct",
            "ram_usada_mb",
            "ram_total_mb",
            "disco_usado_gb",
            "disco_total_gb",
            "ultima_conexion",
        ]
    )
    for d in db.query(Device).order_by(Device.hostname).all():
        writer.writerow(
            [
                d.hostname,
                d.status,
                d.os_name,
                d.os_version,
                d.ip_address,
                d.mac_address,
                d.logged_user,
                d.cpu_percent,
                d.ram_used_mb,
                d.ram_total_mb,
                d.disk_used_gb,
                d.disk_total_gb,
                d.last_seen_at.isoformat() if d.last_seen_at else "",
            ]
        )
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=inventario.csv"},
    )
