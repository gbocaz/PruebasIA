from datetime import datetime

from sqlalchemy.orm import Session

from app.models.device import Device, NetworkInterface
from app.models.software import DeviceSoftware, Software
from app.models.user import utcnow


def _norm(value: str) -> str:
    return " ".join(value.strip().lower().split())


def upsert_software_inventory(db: Session, device: Device, items: list[dict], seen_at: datetime | None = None) -> int:
    seen_at = seen_at or utcnow()
    seen_ids: set[str] = set()
    for item in items:
        name = item["name"].strip()
        if not name:
            continue
        publisher = (item.get("publisher") or "").strip()
        version = (item.get("version") or "").strip()
        n_name = _norm(name)
        n_pub = _norm(publisher)
        software = (
            db.query(Software)
            .filter(Software.name_normalized == n_name, Software.publisher_normalized == n_pub)
            .one_or_none()
        )
        if software is None:
            software = Software(
                name=name[:255],
                name_normalized=n_name[:255],
                publisher=publisher[:255],
                publisher_normalized=n_pub[:255],
            )
            db.add(software)
            db.flush()
        link = (
            db.query(DeviceSoftware)
            .filter(DeviceSoftware.device_id == device.id, DeviceSoftware.software_id == software.id)
            .one_or_none()
        )
        if link is None:
            db.add(
                DeviceSoftware(
                    device_id=device.id,
                    software_id=software.id,
                    version=version[:128],
                    detected_at=seen_at,
                    last_seen_at=seen_at,
                    updated_at=seen_at,
                )
            )
        else:
            if version and version != link.version:
                link.version = version[:128]
                link.updated_at = seen_at
            link.last_seen_at = seen_at
        seen_ids.add(software.id)
    return len(seen_ids)


def replace_interfaces(db: Session, device: Device, interfaces: list[dict]) -> None:
    db.query(NetworkInterface).filter(NetworkInterface.device_id == device.id).delete()
    for iface in interfaces:
        db.add(
            NetworkInterface(
                device_id=device.id,
                name=iface.get("name") or "",
                mac=iface.get("mac") or "",
                ipv4=iface.get("ipv4") or "",
                ipv6=iface.get("ipv6") or "",
                is_up=bool(iface.get("is_up", True)),
                speed_mbps=int(iface.get("speed_mbps") or 0),
                bytes_sent=int(iface.get("bytes_sent") or 0),
                bytes_recv=int(iface.get("bytes_recv") or 0),
            )
        )
