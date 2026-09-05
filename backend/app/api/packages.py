import hashlib
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.enums import OsFamily
from app.models.software import SoftwarePackage
from app.models.user import User, new_id
from app.schemas.ops import PackageOut
from app.security.audit import write_audit
from app.security.deps import get_current_user
from app.security.rbac import ADMIN_ROLES, READ_ROLES, client_ip, require_roles
from app.security.tokens import utcnow

router = APIRouter(prefix="/api/packages", tags=["packages"])


@router.get("", response_model=list[PackageOut])
def list_packages(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_roles(user, READ_ROLES)
    return db.query(SoftwarePackage).order_by(SoftwarePackage.created_at.desc()).all()


@router.post("", response_model=PackageOut, status_code=201)
async def upload_package(
    request: Request,
    name: str = Form(...),
    version: str = Form(...),
    os_family: OsFamily = Form(...),
    architecture: str = Form("any"),
    install_command: str = Form(...),
    notes: str = Form(""),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_roles(user, ADMIN_ROLES)
    settings = get_settings()
    data = await file.read()
    max_bytes = settings.max_package_mb * 1024 * 1024
    if len(data) > max_bytes:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Archivo demasiado grande")
    if not install_command.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El comando de instalación es obligatorio")
    digest = hashlib.sha256(data).hexdigest()
    pkg_id = new_id()
    dest_dir = Path(settings.upload_dir) / pkg_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    filename = Path(file.filename or "installer.bin").name
    dest = dest_dir / filename
    dest.write_bytes(data)
    row = SoftwarePackage(
        id=pkg_id,
        name=name,
        version=version,
        os_family=os_family.value,
        architecture=architecture,
        sha256=digest,
        install_command=install_command.strip(),
        original_filename=filename,
        storage_path=str(dest),
        size_bytes=len(data),
        created_by=user.id,
        notes=notes,
        created_at=utcnow(),
    )
    db.add(row)
    db.flush()
    write_audit(
        db,
        user=user,
        ip=client_ip(request),
        action="package_upload",
        target_type="package",
        target_id=pkg_id,
        details=digest,
    )
    return row


@router.delete("/{package_id}")
def delete_package(
    package_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_roles(user, ADMIN_ROLES)
    row = db.get(SoftwarePackage, package_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Paquete no encontrado")
    path = Path(row.storage_path)
    if path.exists():
        path.unlink()
    db.delete(row)
    write_audit(db, user=user, ip=client_ip(request), action="package_delete", target_type="package", target_id=package_id)
    return {"ok": True}
