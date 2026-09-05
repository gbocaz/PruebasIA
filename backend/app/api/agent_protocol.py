import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.enums import InstallStatus, TaskStatus
from app.limiter import limiter
from app.models.device import Agent, Device, DeviceEvent, DeviceGroupMember, DeviceMetric
from app.models.software import InstallJob, InstallJobDevice, SoftwarePackage
from app.models.user import EnrollmentToken
from app.schemas.ops import EnrollIn, HeartbeatIn, InventoryIn, TaskResultIn
from app.security.agent_auth import get_current_agent
from app.security.crypto import encrypt_secret
from app.security.tokens import new_token, sha256_hex, utcnow, canonical_iso, as_utc
from app.services.inventory import replace_interfaces, upsert_software_inventory
from app.services.network import link_managed_device
from app.services.status import alert_unauthorized_software, apply_status_and_alerts
from app.services.tasks import pending_tasks

router = APIRouter(prefix="/agent", tags=["agent-protocol"])


@router.post("/enroll")
@limiter.limit("10/minute")
def enroll(request: Request, body: EnrollIn, db: Session = Depends(get_db)):
    token_hash = sha256_hex(body.token)
    row = db.query(EnrollmentToken).filter(EnrollmentToken.token_hash == token_hash).one_or_none()
    now = utcnow()
    expires = as_utc(row.expires_at) if row is not None else None
    if (
        row is None
        or row.revoked_at is not None
        or (expires and expires < now)
        or row.use_count >= row.max_uses
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token de enrolamiento inválido")
    settings = get_settings()
    device = Device(
        hostname=body.hostname,
        display_name=body.hostname,
        os_family=body.os_family.value,
        os_name=body.os_name,
        os_version=body.os_version,
        architecture=body.architecture,
        agent_version=body.agent_version,
        status="offline",
    )
    db.add(device)
    db.flush()
    if row.group_id:
        db.add(DeviceGroupMember(device_id=device.id, group_id=row.group_id))
    agent_token = new_token(32)
    hmac_secret = new_token(32)
    agent = Agent(
        device_id=device.id,
        token_hash=sha256_hex(agent_token),
        hmac_secret_encrypted=encrypt_secret(hmac_secret),
        version=body.agent_version,
        heartbeat_interval_seconds=settings.default_heartbeat_seconds,
    )
    db.add(agent)
    row.use_count += 1
    db.add(DeviceEvent(device_id=device.id, type="enrolled", message="Agente enrolado"))
    return {
        "device_id": device.id,
        "agent_id": agent.id,
        "agent_token": agent_token,
        "hmac_secret": hmac_secret,
        "heartbeat_interval_seconds": settings.default_heartbeat_seconds,
        "server_time": now.isoformat(),
    }


def _apply_heartbeat(db: Session, agent: Agent, body: HeartbeatIn) -> Device:
    device = agent.device
    previous = device.status
    device.hostname = body.hostname or device.hostname
    device.os_family = body.os_family.value
    device.os_name = body.os_name
    device.os_version = body.os_version
    device.architecture = body.architecture
    device.ip_address = body.ip_address
    device.mac_address = body.mac_address
    device.logged_user = body.logged_user
    device.cpu_model = body.cpu_model
    device.cpu_percent = body.cpu_percent
    device.ram_total_mb = body.ram_total_mb
    device.ram_used_mb = body.ram_used_mb
    device.disk_total_gb = body.disk_total_gb
    device.disk_used_gb = body.disk_used_gb
    device.uptime_seconds = body.uptime_seconds
    device.agent_version = body.agent_version
    device.last_seen_at = utcnow()
    agent.last_seen_at = device.last_seen_at
    agent.version = body.agent_version or agent.version
    db.add(
        DeviceMetric(
            device_id=device.id,
            cpu_percent=body.cpu_percent,
            ram_used_mb=body.ram_used_mb,
            ram_total_mb=body.ram_total_mb,
            disk_used_gb=body.disk_used_gb,
            disk_total_gb=body.disk_total_gb,
            bytes_sent=body.bytes_sent,
            bytes_recv=body.bytes_recv,
        )
    )
    if body.interfaces:
        replace_interfaces(db, device, [i.model_dump() for i in body.interfaces])
    link_managed_device(db, device)
    apply_status_and_alerts(db, device, previous)
    return device


@router.post("/heartbeat")
@limiter.limit(get_settings().rate_limit_agent)
def heartbeat(request: Request, body: HeartbeatIn, db: Session = Depends(get_db), agent: Agent = Depends(get_current_agent)):
    device = _apply_heartbeat(db, agent, body)
    return {
        "ok": True,
        "device_id": device.id,
        "status": device.status,
        "heartbeat_interval_seconds": agent.heartbeat_interval_seconds,
    }


@router.post("/inventory")
@limiter.limit(get_settings().rate_limit_agent)
def inventory(request: Request, body: InventoryIn, db: Session = Depends(get_db), agent: Agent = Depends(get_current_agent)):
    device = agent.device
    count = upsert_software_inventory(db, device, [i.model_dump() for i in body.software])
    if body.interfaces:
        replace_interfaces(db, device, [i.model_dump() for i in body.interfaces])
    alert_unauthorized_software(db, device)
    db.add(DeviceEvent(device_id=device.id, type="inventory", message=f"{count} programas"))
    return {"ok": True, "software_count": count}


@router.post("/metrics")
@limiter.limit(get_settings().rate_limit_agent)
def metrics(request: Request, body: HeartbeatIn, db: Session = Depends(get_db), agent: Agent = Depends(get_current_agent)):
    _apply_heartbeat(db, agent, body)
    return {"ok": True}


@router.get("/tasks")
@limiter.limit(get_settings().rate_limit_agent)
def tasks(request: Request, db: Session = Depends(get_db), agent: Agent = Depends(get_current_agent)):
    rows = pending_tasks(db, agent.device_id)
    return [
        {
            "task_id": t.id,
            "device_id": t.device_id,
            "type": t.type,
            "params": json.loads(t.payload_json or "{}"),
            "signature": t.signature,
            "created_at": canonical_iso(t.created_at),
            "expires_at": canonical_iso(t.expires_at),
        }
        for t in rows
    ]


@router.post("/task-result")
@limiter.limit(get_settings().rate_limit_agent)
def task_result(request: Request, body: TaskResultIn, db: Session = Depends(get_db), agent: Agent = Depends(get_current_agent)):
    from app.models.device import AgentTask

    task = db.get(AgentTask, body.task_id)
    if task is None or task.device_id != agent.device_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tarea no encontrada")
    if task.status == TaskStatus.COMPLETED.value:
        return {"ok": True, "idempotent": True}
    task.status = TaskStatus.COMPLETED.value if body.success else TaskStatus.FAILED.value
    task.result_json = json.dumps({"message": body.message, "extra": body.extra_json}, ensure_ascii=False)
    task.completed_at = utcnow()
    install = db.query(InstallJobDevice).filter(InstallJobDevice.task_id == task.id).one_or_none()
    if install:
        install.status = InstallStatus.INSTALADO.value if body.success else InstallStatus.ERROR.value
        install.message = body.message
        install.updated_at = utcnow()
    db.add(
        DeviceEvent(
            device_id=agent.device_id,
            type="task_result",
            message=f"{task.type}: {'ok' if body.success else 'error'} {body.message}",
        )
    )
    return {"ok": True}


@router.get("/packages/{package_id}/download")
def download_package(package_id: str, db: Session = Depends(get_db), agent: Agent = Depends(get_current_agent)):
    pkg = db.get(SoftwarePackage, package_id)
    if pkg is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Paquete no encontrado")
    assignment = (
        db.query(InstallJobDevice)
        .join(InstallJob, InstallJob.id == InstallJobDevice.job_id)
        .filter(
            InstallJobDevice.device_id == agent.device_id,
            InstallJob.package_id == package_id,
            InstallJobDevice.status.in_(
                [
                    InstallStatus.PENDIENTE.value,
                    InstallStatus.DESCARGANDO.value,
                    InstallStatus.INSTALANDO.value,
                ]
            ),
        )
        .order_by(InstallJobDevice.updated_at.desc())
        .first()
    )
    if assignment is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Este paquete no está asignado al equipo")
    path = Path(pkg.storage_path)
    if not path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Archivo no disponible")
    assignment.status = InstallStatus.DESCARGANDO.value
    assignment.updated_at = utcnow()
    return FileResponse(path, filename=pkg.original_filename, media_type="application/octet-stream")
