import ipaddress
import json
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.limiter import limiter
from app.models.network import (
    NetworkCollector,
    NetworkCredential,
    NetworkDevice,
    NetworkLink,
    NetworkScanJob,
)
from app.schemas.network import CollectorHeartbeat, ScanResultIn
from app.security.collector_auth import get_current_collector
from app.security.crypto import decrypt_secret
from app.security.tokens import utcnow
from app.services.network import scan_to_out, validate_private_cidrs

router = APIRouter(prefix="/collector", tags=["network-collector-protocol"])


@router.post("/heartbeat")
@limiter.limit("120/minute")
def heartbeat(
    request: Request,
    body: CollectorHeartbeat,
    collector: NetworkCollector = Depends(get_current_collector),
):
    collector.hostname = body.hostname
    collector.version = body.version
    collector.last_seen_at = utcnow()
    return {"ok": True, "collector_id": collector.id, "site_id": collector.site_id}


@router.get("/config")
@limiter.limit("30/minute")
def collector_config(
    request: Request,
    db: Session = Depends(get_db),
    collector: NetworkCollector = Depends(get_current_collector),
):
    site = collector.site
    cidrs = validate_private_cidrs(json.loads(site.cidrs_json or "[]"), site.max_hosts_per_scan)
    rows = (
        db.query(NetworkCredential)
        .filter(NetworkCredential.site_id == site.id, NetworkCredential.enabled.is_(True))
        .all()
    )
    credentials = []
    for row in rows:
        credentials.append(
            {
                "id": row.id,
                "name": row.name,
                "kind": row.kind,
                "username": row.username,
                "secret": decrypt_secret(row.secret_encrypted),
                "auth_protocol": row.auth_protocol,
                "privacy_protocol": row.privacy_protocol,
                "privacy_secret": (
                    decrypt_secret(row.privacy_secret_encrypted) if row.privacy_secret_encrypted else ""
                ),
            }
        )
    response = JSONResponse(
        {
            "site_id": site.id,
            "site_name": site.name,
            "cidrs": cidrs,
            "max_hosts": site.max_hosts_per_scan,
            "tcp_ports": [22, 80, 443, 3389, 5900, 5985, 5986],
            "credentials": credentials,
        }
    )
    response.headers["Cache-Control"] = "no-store"
    return response


@router.get("/tasks")
@limiter.limit("60/minute")
def collector_tasks(
    request: Request,
    db: Session = Depends(get_db),
    collector: NetworkCollector = Depends(get_current_collector),
):
    rows = (
        db.query(NetworkScanJob)
        .filter(
            NetworkScanJob.collector_id == collector.id,
            NetworkScanJob.status.in_(["pending", "sent"]),
        )
        .order_by(NetworkScanJob.requested_at.asc())
        .limit(5)
        .all()
    )
    output = []
    for row in rows:
        if row.status == "pending":
            row.status = "sent"
        output.append(
            {
                "scan_id": row.id,
                "site_id": row.site_id,
                "methods": json.loads(row.methods_json or "[]"),
                "requested_at": row.requested_at,
            }
        )
    return output


def _ip_allowed(ip_text: str, networks: list[ipaddress._BaseNetwork]) -> bool:
    try:
        ip = ipaddress.ip_address(ip_text)
    except ValueError:
        return False
    return any(ip in network for network in networks)


def _safe_management_url(url: str, ip_address: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or parsed.hostname != ip_address:
        return ""
    return url[:512]


@router.post("/scans/{scan_id}/results")
@limiter.limit("20/minute")
def scan_results(
    scan_id: str,
    request: Request,
    body: ScanResultIn,
    db: Session = Depends(get_db),
    collector: NetworkCollector = Depends(get_current_collector),
):
    scan = db.get(NetworkScanJob, scan_id)
    if scan is None or scan.collector_id != collector.id or scan.site_id != collector.site_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Escaneo no encontrado")
    if scan.status == "completed":
        return {"ok": True, "idempotent": True, "result_count": scan.result_count}
    scan.started_at = scan.started_at or utcnow()
    if body.error:
        scan.status = "failed"
        scan.error = body.error
        scan.completed_at = utcnow()
        return {"ok": False, "error": body.error}

    site = collector.site
    cidrs = validate_private_cidrs(json.loads(site.cidrs_json or "[]"), site.max_hosts_per_scan)
    networks = [ipaddress.ip_network(cidr, strict=False) for cidr in cidrs]
    seen: set[str] = set()
    now = utcnow()
    for item in body.devices:
        if not _ip_allowed(item.ip_address, networks):
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"El resultado {item.ip_address} está fuera de los CIDR autorizados",
            )
        identity = item.identity_key.lower()
        row = (
            db.query(NetworkDevice)
            .filter(NetworkDevice.site_id == site.id, NetworkDevice.identity_key == identity)
            .one_or_none()
        )
        if row is None:
            row = NetworkDevice(site_id=site.id, identity_key=identity, first_seen_at=now)
            db.add(row)
        row.ip_address = item.ip_address
        row.mac_address = item.mac_address.lower()
        row.hostname = item.hostname
        row.vendor = item.vendor
        row.model = item.model
        row.serial_number = item.serial_number
        row.device_type = item.device_type
        row.os_name = item.os_name
        row.status = item.status
        row.discovery_source = item.discovery_source
        row.sys_name = item.sys_name
        row.sys_description = item.sys_description
        row.sys_object_id = item.sys_object_id
        row.open_ports_json = json.dumps(sorted(set(item.open_ports)))
        row.remote_services_json = json.dumps(
            sorted(set(item.remote_services).intersection({"rdp", "vnc", "ssh", "http", "https"}))
        )
        row.management_url = _safe_management_url(item.management_url, item.ip_address)
        row.switch_port = item.switch_port
        row.vlan = item.vlan
        row.ssid = item.ssid
        row.last_seen_at = now
        seen.add(identity)
    if seen:
        stale = (
            db.query(NetworkDevice)
            .filter(NetworkDevice.site_id == site.id, ~NetworkDevice.identity_key.in_(seen))
            .all()
        )
    else:
        stale = db.query(NetworkDevice).filter(NetworkDevice.site_id == site.id).all()
    for row in stale:
        row.status = "offline"

    db.query(NetworkLink).filter(NetworkLink.site_id == site.id).delete()
    for link in body.links:
        db.add(
            NetworkLink(
                site_id=site.id,
                source_identity=link.source_identity.lower(),
                target_identity=link.target_identity.lower(),
                source_port=link.source_port,
                target_port=link.target_port,
                protocol=link.protocol,
                last_seen_at=now,
            )
        )
    scan.status = "completed"
    scan.result_count = len(seen)
    scan.completed_at = now
    scan.error = ""
    return {"ok": True, "result_count": len(seen)}
