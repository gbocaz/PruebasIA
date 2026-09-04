from datetime import timedelta

from sqlalchemy.orm import Session

from app.config import get_settings
from app.enums import AlertLevel, DeviceStatus, SoftwareCategory
from app.models.device import Device
from app.models.ops import Alert
from app.models.software import DeviceSoftware, Software
from app.models.user import utcnow


MANUAL_STATUSES = {DeviceStatus.EXCLUIDO.value, DeviceStatus.MANTENIMIENTO.value}


def derive_runtime_status(device: Device) -> str:
    if device.status in MANUAL_STATUSES:
        return device.status
    settings = get_settings()
    interval = settings.default_heartbeat_seconds
    if device.agent:
        interval = device.agent.heartbeat_interval_seconds or interval
    if device.last_seen_at is None:
        return DeviceStatus.OFFLINE.value
    last = device.last_seen_at
    if last.tzinfo is None:
        from datetime import timezone

        last = last.replace(tzinfo=timezone.utc)
    stale_after = timedelta(seconds=interval * settings.heartbeat_offline_factor)
    if utcnow() - last > stale_after:
        return DeviceStatus.OFFLINE.value
    if device.disk_total_gb and (device.disk_used_gb / device.disk_total_gb) >= 0.95:
        return DeviceStatus.CRITICO.value
    if device.cpu_percent >= 95:
        return DeviceStatus.CRITICO.value
    if device.disk_total_gb and (device.disk_used_gb / device.disk_total_gb) >= 0.85:
        return DeviceStatus.ADVERTENCIA.value
    if device.cpu_percent >= 90:
        return DeviceStatus.ADVERTENCIA.value
    if device.ram_total_mb and (device.ram_used_mb / device.ram_total_mb) >= 0.90:
        return DeviceStatus.ADVERTENCIA.value
    return DeviceStatus.ONLINE.value


def open_alert(db: Session, *, level: AlertLevel, title: str, message: str, device_id: str | None) -> None:
    existing = (
        db.query(Alert)
        .filter(
            Alert.device_id == device_id,
            Alert.title == title,
            Alert.acknowledged.is_(False),
        )
        .first()
    )
    if existing:
        return
    db.add(Alert(level=level.value, title=title, message=message, device_id=device_id))


def apply_status_and_alerts(db: Session, device: Device, previous_status: str) -> None:
    new_status = derive_runtime_status(device)
    device.status = new_status
    if previous_status != DeviceStatus.OFFLINE.value and new_status == DeviceStatus.OFFLINE.value:
        open_alert(
            db,
            level=AlertLevel.IMPORTANTE,
            title=f"{device.hostname} OFFLINE",
            message=f"El equipo no envía heartbeat. Último contacto: {device.last_seen_at}",
            device_id=device.id,
        )
    if new_status == DeviceStatus.CRITICO.value:
        open_alert(
            db,
            level=AlertLevel.CRITICO,
            title=f"{device.hostname} CRÍTICO",
            message=f"CPU {device.cpu_percent:.0f}% · disco {device.disk_used_gb:.1f}/{device.disk_total_gb:.1f} GB",
            device_id=device.id,
        )
    elif new_status == DeviceStatus.ADVERTENCIA.value:
        open_alert(
            db,
            level=AlertLevel.ADVERTENCIA,
            title=f"{device.hostname} en advertencia",
            message=f"CPU {device.cpu_percent:.0f}% · RAM {device.ram_used_mb}/{device.ram_total_mb} MB",
            device_id=device.id,
        )


def alert_unauthorized_software(db: Session, device: Device) -> None:
    if device.exclude_software:
        return
    rows = (
        db.query(Software)
        .join(DeviceSoftware, DeviceSoftware.software_id == Software.id)
        .filter(DeviceSoftware.device_id == device.id, Software.category == SoftwareCategory.NO_AUTORIZADO.value)
        .all()
    )
    for sw in rows:
        open_alert(
            db,
            level=AlertLevel.IMPORTANTE,
            title=f"{device.hostname} tiene software no autorizado",
            message=f"{sw.name} ({sw.publisher}) está clasificado como no autorizado.",
            device_id=device.id,
        )


def refresh_offline_devices(db: Session) -> int:
    changed = 0
    for device in db.query(Device).all():
        prev = device.status
        apply_status_and_alerts(db, device, prev)
        if device.status != prev:
            changed += 1
    return changed
