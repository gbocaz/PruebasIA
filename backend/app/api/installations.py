from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.enums import InstallStatus, TaskType
from app.models.device import Device, DeviceGroupMember, DeviceEvent
from app.models.software import InstallJob, InstallJobDevice, SoftwarePackage
from app.models.user import User
from app.schemas.ops import InstallCreate
from app.security.audit import write_audit
from app.security.deps import get_current_user
from app.security.rbac import ADMIN_ROLES, READ_ROLES, client_ip, require_roles
from app.services.tasks import create_task

router = APIRouter(prefix="/api/installations", tags=["installations"])


def _targets(db: Session, body: InstallCreate) -> list[Device]:
    if body.target_type == "all":
        return db.query(Device).all()
    if body.target_type == "device":
        device = db.get(Device, body.target_id)
        if device is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Equipo no encontrado")
        return [device]
    links = db.query(DeviceGroupMember).filter(DeviceGroupMember.group_id == body.target_id).all()
    ids = [l.device_id for l in links]
    if not ids:
        return []
    return db.query(Device).filter(Device.id.in_(ids)).all()


@router.get("")
def list_jobs(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_roles(user, READ_ROLES)
    jobs = (
        db.query(InstallJob)
        .options(joinedload(InstallJob.package), joinedload(InstallJob.devices))
        .order_by(InstallJob.created_at.desc())
        .limit(100)
        .all()
    )
    out = []
    for job in jobs:
        out.append(
            {
                "id": job.id,
                "package_name": job.package.name if job.package else "",
                "package_version": job.package.version if job.package else "",
                "target_type": job.target_type,
                "created_at": job.created_at,
                "devices": [
                    {"device_id": d.device_id, "status": d.status, "message": d.message} for d in job.devices
                ],
            }
        )
    return out


@router.post("", status_code=201)
def create_install(
    request: Request,
    body: InstallCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_roles(user, ADMIN_ROLES)
    if body.target_type in {"all", "group"} and not body.confirm:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La instalación masiva requiere confirmación")
    package = db.get(SoftwarePackage, body.package_id)
    if package is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Paquete no encontrado")
    devices = _targets(db, body)
    matching = [d for d in devices if d.os_family == package.os_family or package.os_family == "other"]
    if not matching:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No hay equipos compatibles con este paquete")
    job = InstallJob(
        package_id=package.id,
        created_by=user.id,
        target_type=body.target_type,
        target_id=body.target_id,
        notes=body.notes,
    )
    db.add(job)
    db.flush()
    queued = 0
    for device in matching:
        try:
            task = create_task(
                db,
                device,
                TaskType.INSTALL_PACKAGE,
                {
                    "package_id": package.id,
                    "sha256": package.sha256,
                    "install_command": package.install_command,
                    "filename": package.original_filename,
                },
            )
        except ValueError:
            db.add(
                InstallJobDevice(
                    job_id=job.id,
                    device_id=device.id,
                    status=InstallStatus.ERROR.value,
                    message="Sin agente activo",
                )
            )
            continue
        db.add(
            InstallJobDevice(
                job_id=job.id,
                device_id=device.id,
                task_id=task.id,
                status=InstallStatus.PENDIENTE.value,
            )
        )
        db.add(DeviceEvent(device_id=device.id, type="install_queued", message=f"{package.name} {package.version}"))
        queued += 1
    write_audit(
        db,
        user=user,
        ip=client_ip(request),
        action="install_create",
        target_type="package",
        target_id=package.id,
        details=f"job={job.id} equipos={queued}",
    )
    return {"job_id": job.id, "queued": queued}
