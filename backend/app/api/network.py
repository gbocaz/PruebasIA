import json
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.network import (
    NetworkCollector,
    NetworkCredential,
    NetworkDevice,
    NetworkLink,
    NetworkScanJob,
    NetworkSite,
)
from app.models.user import User
from app.schemas.network import (
    CollectorCreate,
    CollectorOut,
    CredentialCreate,
    CredentialOut,
    NetworkDeviceOut,
    NetworkSiteIn,
    NetworkSiteOut,
    RemoteSessionRequest,
    ScanCreate,
    ScanOut,
)
from app.security.audit import write_audit
from app.security.crypto import encrypt_secret
from app.security.deps import get_current_user
from app.security.rbac import ADMIN_ROLES, READ_ROLES, SUPPORT_ACTIONS, client_ip, require_roles
from app.security.tokens import new_token, sha256_hex, utcnow
from app.services.network import (
    collector_online,
    device_to_out,
    remote_target,
    scan_to_out,
    site_to_out,
    validate_private_cidrs,
)

router = APIRouter(prefix="/api/network", tags=["network"])


@router.get("/sites", response_model=list[NetworkSiteOut])
def list_sites(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_roles(user, READ_ROLES)
    sites = db.query(NetworkSite).options(joinedload(NetworkSite.collectors)).order_by(NetworkSite.name).all()
    counts = dict(
        db.query(NetworkDevice.site_id, func.count(NetworkDevice.id)).group_by(NetworkDevice.site_id).all()
    )
    return [site_to_out(site, int(counts.get(site.id, 0))) for site in sites]


@router.post("/sites", response_model=NetworkSiteOut, status_code=201)
def create_site(
    request: Request,
    body: NetworkSiteIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_roles(user, ADMIN_ROLES)
    cidrs = validate_private_cidrs(body.cidrs, body.max_hosts_per_scan)
    if db.query(NetworkSite).filter(NetworkSite.name == body.name).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "La sede ya existe")
    site = NetworkSite(
        name=body.name,
        description=body.description,
        location=body.location,
        cidrs_json=json.dumps(cidrs),
        enabled=body.enabled,
        max_hosts_per_scan=body.max_hosts_per_scan,
    )
    db.add(site)
    db.flush()
    write_audit(
        db,
        user=user,
        ip=client_ip(request),
        action="network_site_create",
        target_type="network_site",
        target_id=site.id,
        details=", ".join(cidrs),
    )
    return site_to_out(site)


@router.patch("/sites/{site_id}", response_model=NetworkSiteOut)
def update_site(
    site_id: str,
    request: Request,
    body: NetworkSiteIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_roles(user, ADMIN_ROLES)
    site = db.get(NetworkSite, site_id)
    if site is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sede no encontrada")
    cidrs = validate_private_cidrs(body.cidrs, body.max_hosts_per_scan)
    site.name = body.name
    site.description = body.description
    site.location = body.location
    site.cidrs_json = json.dumps(cidrs)
    site.enabled = body.enabled
    site.max_hosts_per_scan = body.max_hosts_per_scan
    write_audit(
        db,
        user=user,
        ip=client_ip(request),
        action="network_site_update",
        target_type="network_site",
        target_id=site.id,
    )
    count = db.query(NetworkDevice).filter(NetworkDevice.site_id == site.id).count()
    return site_to_out(site, count)


@router.get("/sites/{site_id}/collectors", response_model=list[CollectorOut])
def list_collectors(site_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_roles(user, READ_ROLES)
    rows = (
        db.query(NetworkCollector)
        .filter(NetworkCollector.site_id == site_id)
        .order_by(NetworkCollector.created_at.desc())
        .all()
    )
    return [_collector_out(row) for row in rows]


def _collector_out(row: NetworkCollector, token: str | None = None) -> CollectorOut:
    return CollectorOut(
        id=row.id,
        site_id=row.site_id,
        name=row.name,
        token=token,
        token_prefix=row.token_prefix,
        hostname=row.hostname,
        version=row.version,
        online=collector_online(row),
        last_seen_at=row.last_seen_at,
        revoked=row.revoked,
        created_at=row.created_at,
    )


@router.post("/sites/{site_id}/collectors", response_model=CollectorOut, status_code=201)
def create_collector(
    site_id: str,
    request: Request,
    body: CollectorCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_roles(user, ADMIN_ROLES)
    if db.get(NetworkSite, site_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sede no encontrada")
    token = new_token(32)
    row = NetworkCollector(
        site_id=site_id,
        name=body.name,
        token_hash=sha256_hex(token),
        token_prefix=token[:8],
        created_by=user.id,
    )
    db.add(row)
    db.flush()
    write_audit(
        db,
        user=user,
        ip=client_ip(request),
        action="network_collector_create",
        target_type="network_collector",
        target_id=row.id,
    )
    return _collector_out(row, token)


@router.post("/collectors/{collector_id}/revoke")
def revoke_collector(
    collector_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_roles(user, ADMIN_ROLES)
    row = db.get(NetworkCollector, collector_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recolector no encontrado")
    row.revoked = True
    write_audit(
        db,
        user=user,
        ip=client_ip(request),
        action="network_collector_revoke",
        target_type="network_collector",
        target_id=row.id,
    )
    return {"ok": True}


@router.get("/sites/{site_id}/credentials", response_model=list[CredentialOut])
def list_credentials(site_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_roles(user, ADMIN_ROLES)
    return (
        db.query(NetworkCredential)
        .filter(NetworkCredential.site_id == site_id)
        .order_by(NetworkCredential.created_at.desc())
        .all()
    )


@router.post("/sites/{site_id}/credentials", response_model=CredentialOut, status_code=201)
def create_credential(
    site_id: str,
    request: Request,
    body: CredentialCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_roles(user, ADMIN_ROLES)
    if db.get(NetworkSite, site_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sede no encontrada")
    if body.kind == "snmp_v3" and not body.username:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "SNMPv3 requiere usuario")
    if body.privacy_protocol != "NONE" and body.kind == "snmp_v3" and not body.privacy_secret:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "SNMPv3 con privacidad requiere clave privada")
    row = NetworkCredential(
        site_id=site_id,
        name=body.name,
        kind=body.kind,
        username=body.username,
        secret_encrypted=encrypt_secret(body.secret),
        auth_protocol=body.auth_protocol,
        privacy_protocol=body.privacy_protocol,
        privacy_secret_encrypted=encrypt_secret(body.privacy_secret) if body.privacy_secret else "",
        enabled=body.enabled,
        created_by=user.id,
    )
    db.add(row)
    db.flush()
    write_audit(
        db,
        user=user,
        ip=client_ip(request),
        action="network_credential_create",
        target_type="network_credential",
        target_id=row.id,
        details=f"{row.kind}:{row.name}",
    )
    return row


@router.delete("/credentials/{credential_id}")
def delete_credential(
    credential_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_roles(user, ADMIN_ROLES)
    row = db.get(NetworkCredential, credential_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Credencial no encontrada")
    db.delete(row)
    write_audit(
        db,
        user=user,
        ip=client_ip(request),
        action="network_credential_delete",
        target_type="network_credential",
        target_id=credential_id,
    )
    return {"ok": True}


@router.get("/scans", response_model=list[ScanOut])
def list_scans(
    site_id: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_roles(user, READ_ROLES)
    query = db.query(NetworkScanJob)
    if site_id:
        query = query.filter(NetworkScanJob.site_id == site_id)
    return [scan_to_out(row) for row in query.order_by(NetworkScanJob.requested_at.desc()).limit(100).all()]


@router.post("/scans", response_model=ScanOut, status_code=201)
def create_scan(
    request: Request,
    body: ScanCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_roles(user, ADMIN_ROLES)
    if not body.confirm:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El escaneo de red requiere confirmación")
    site = db.get(NetworkSite, body.site_id)
    if site is None or not site.enabled:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sede no encontrada o desactivada")
    validate_private_cidrs(json.loads(site.cidrs_json), site.max_hosts_per_scan)
    running = (
        db.query(NetworkScanJob)
        .filter(
            NetworkScanJob.site_id == site.id,
            NetworkScanJob.status.in_(["pending", "sent", "running"]),
        )
        .first()
    )
    if running:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe un escaneo pendiente o activo")
    collector = (
        db.query(NetworkCollector)
        .filter(NetworkCollector.site_id == site.id, NetworkCollector.revoked.is_(False))
        .order_by(NetworkCollector.last_seen_at.desc())
        .first()
    )
    if collector is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "La sede no tiene recolector activo")
    row = NetworkScanJob(
        site_id=site.id,
        collector_id=collector.id,
        methods_json=json.dumps(body.methods),
        requested_by=user.id,
    )
    db.add(row)
    db.flush()
    write_audit(
        db,
        user=user,
        ip=client_ip(request),
        action="network_scan_create",
        target_type="network_site",
        target_id=site.id,
        details=f"scan={row.id}; methods={','.join(body.methods)}",
    )
    return scan_to_out(row)


@router.get("/devices", response_model=list[NetworkDeviceOut])
def list_network_devices(
    site_id: str | None = None,
    q: str | None = None,
    vendor: str | None = None,
    device_type: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_roles(user, READ_ROLES)
    query = db.query(NetworkDevice)
    if site_id:
        query = query.filter(NetworkDevice.site_id == site_id)
    if vendor:
        query = query.filter(NetworkDevice.vendor == vendor)
    if device_type:
        query = query.filter(NetworkDevice.device_type == device_type)
    if status_filter:
        query = query.filter(NetworkDevice.status == status_filter)
    if q:
        like = f"%{q}%"
        query = query.filter(
            NetworkDevice.ip_address.ilike(like)
            | NetworkDevice.mac_address.ilike(like)
            | NetworkDevice.hostname.ilike(like)
            | NetworkDevice.vendor.ilike(like)
            | NetworkDevice.model.ilike(like)
        )
    rows = query.order_by(NetworkDevice.vendor, NetworkDevice.hostname, NetworkDevice.ip_address).limit(10000).all()
    return [device_to_out(row) for row in rows]


@router.get("/devices/{device_id}", response_model=NetworkDeviceOut)
def get_network_device(
    device_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_roles(user, READ_ROLES)
    row = db.get(NetworkDevice, device_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dispositivo no encontrado")
    return device_to_out(row)


@router.get("/links")
def list_links(
    site_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_roles(user, READ_ROLES)
    rows = db.query(NetworkLink).filter(NetworkLink.site_id == site_id).all()
    return [
        {
            "id": row.id,
            "source_identity": row.source_identity,
            "target_identity": row.target_identity,
            "source_port": row.source_port,
            "target_port": row.target_port,
            "protocol": row.protocol,
            "last_seen_at": row.last_seen_at,
        }
        for row in rows
    ]


@router.post("/devices/{device_id}/remote-session")
def create_remote_session(
    device_id: str,
    request: Request,
    body: RemoteSessionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_roles(user, SUPPORT_ACTIONS)
    if not body.confirm:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La conexión remota requiere confirmación")
    device = db.get(NetworkDevice, device_id)
    if device is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dispositivo no encontrado")
    target = remote_target(device, body.protocol, body.username)
    write_audit(
        db,
        user=user,
        ip=client_ip(request),
        action="network_remote_session",
        target_type="network_device",
        target_id=device.id,
        details=f"protocol={body.protocol}; destination={device.ip_address}",
    )
    if target["kind"] == "file":
        return Response(
            target["content"],
            media_type="application/x-rdp",
            headers={"Content-Disposition": f'attachment; filename="{target["filename"]}"'},
        )
    return target
