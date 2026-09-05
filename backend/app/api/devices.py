from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.enums import DeviceStatus, TaskType
from app.models.device import Device, DeviceEvent, DeviceGroupMember, DeviceMetric, NetworkInterface
from app.models.software import DeviceSoftware
from app.models.user import User
from app.schemas.ops import (
    DeviceActionRequest,
    DeviceOut,
    DeviceSoftwareOut,
    DeviceUpdate,
    EventOut,
    InterfaceOut,
    MetricOut,
)
from app.security.audit import write_audit
from app.security.deps import get_current_user
from app.security.rbac import ADMIN_ROLES, READ_ROLES, SUPPORT_ACTIONS, client_ip, require_roles
from app.services.devices import device_to_out, set_device_groups
from app.services.tasks import create_task

router = APIRouter(prefix="/api/devices", tags=["devices"])

SOPORTE_ACTIONS = {"collect_inventory"}


@router.get("", response_model=list[DeviceOut])
def list_devices(
    q: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    os_family: str | None = None,
    group_id: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_roles(user, READ_ROLES)
    query = db.query(Device).options(joinedload(Device.group_links).joinedload(DeviceGroupMember.group))
    if status_filter:
        query = query.filter(Device.status == status_filter)
    if os_family:
        query = query.filter(Device.os_family == os_family)
    if q:
        like = f"%{q}%"
        query = query.filter(
            (Device.hostname.ilike(like))
            | (Device.ip_address.ilike(like))
            | (Device.mac_address.ilike(like))
            | (Device.logged_user.ilike(like))
        )
    devices = query.order_by(Device.hostname).all()
    if group_id:
        devices = [d for d in devices if any(link.group_id == group_id for link in d.group_links)]
    return [device_to_out(d) for d in devices]


@router.get("/{device_id}", response_model=DeviceOut)
def get_device(device_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_roles(user, READ_ROLES)
    device = db.get(Device, device_id)
    if device is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Equipo no encontrado")
    return device_to_out(device)


@router.patch("/{device_id}", response_model=DeviceOut)
def update_device(
    device_id: str,
    request: Request,
    body: DeviceUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_roles(user, ADMIN_ROLES)
    device = db.get(Device, device_id)
    if device is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Equipo no encontrado")
    data = body.model_dump(exclude_unset=True)
    group_ids = data.pop("group_ids", None)
    if "status" in data and data["status"] is not None:
        allowed = {DeviceStatus.EXCLUIDO.value, DeviceStatus.MANTENIMIENTO.value, DeviceStatus.ONLINE.value}
        value = data.pop("status").value
        if value not in allowed:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Estado no asignable manualmente")
        device.status = value
    for key, value in data.items():
        setattr(device, key, value)
    if group_ids is not None:
        set_device_groups(db, device, group_ids)
    write_audit(db, user=user, ip=client_ip(request), action="device_update", target_type="device", target_id=device.id)
    return device_to_out(device)


@router.get("/{device_id}/software", response_model=list[DeviceSoftwareOut])
def device_software(device_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_roles(user, READ_ROLES)
    rows = (
        db.query(DeviceSoftware)
        .filter(DeviceSoftware.device_id == device_id)
        .order_by(DeviceSoftware.last_seen_at.desc())
        .all()
    )
    return [
        DeviceSoftwareOut(
            software_id=r.software_id,
            name=r.software.name,
            publisher=r.software.publisher,
            version=r.version,
            category=r.software.category,
            detected_at=r.detected_at,
            last_seen_at=r.last_seen_at,
        )
        for r in rows
        if r.software
    ]


@router.get("/{device_id}/metrics", response_model=list[MetricOut])
def device_metrics(
    device_id: str,
    hours: int = Query(default=24, ge=1, le=24 * 370),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_roles(user, READ_ROLES)
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    return (
        db.query(DeviceMetric)
        .filter(DeviceMetric.device_id == device_id, DeviceMetric.collected_at >= since)
        .order_by(DeviceMetric.collected_at.asc())
        .all()
    )


@router.get("/{device_id}/events", response_model=list[EventOut])
def device_events(device_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_roles(user, READ_ROLES)
    return (
        db.query(DeviceEvent)
        .filter(DeviceEvent.device_id == device_id)
        .order_by(DeviceEvent.created_at.desc())
        .limit(200)
        .all()
    )


@router.get("/{device_id}/interfaces", response_model=list[InterfaceOut])
def device_interfaces(device_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_roles(user, READ_ROLES)
    return db.query(NetworkInterface).filter(NetworkInterface.device_id == device_id).all()


@router.post("/{device_id}/actions")
def device_actions(
    device_id: str,
    request: Request,
    body: DeviceActionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_roles(user, SUPPORT_ACTIONS)
    if user.role not in ADMIN_ROLES and body.action not in SOPORTE_ACTIONS:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Acción no autorizada para este rol")
    if body.action == "restart_agent" and not body.confirm:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Esta acción requiere confirmación")
    device = db.get(Device, device_id)
    if device is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Equipo no encontrado")
    task_type = TaskType.COLLECT_INVENTORY if body.action == "collect_inventory" else TaskType.RESTART_AGENT
    try:
        task = create_task(db, device, task_type, {})
    except ValueError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    db.add(DeviceEvent(device_id=device.id, type=body.action, message=f"Solicitado por {user.username}"))
    write_audit(
        db,
        user=user,
        ip=client_ip(request),
        action=f"device_{body.action}",
        target_type="device",
        target_id=device.id,
        details=task.id,
    )
    return {"task_id": task.id, "status": "queued"}
