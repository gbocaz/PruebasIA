from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.device import DeviceGroup, DeviceGroupMember
from app.models.user import User
from app.schemas.ops import GroupIn, GroupOut
from app.security.audit import write_audit
from app.security.deps import get_current_user
from app.security.rbac import ADMIN_ROLES, READ_ROLES, client_ip, require_roles

router = APIRouter(prefix="/api/groups", tags=["groups"])


@router.get("", response_model=list[GroupOut])
def list_groups(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_roles(user, READ_ROLES)
    groups = db.query(DeviceGroup).order_by(DeviceGroup.name).all()
    out = []
    for g in groups:
        count = db.query(DeviceGroupMember).filter(DeviceGroupMember.group_id == g.id).count()
        out.append(GroupOut.model_validate(g).model_copy(update={"device_count": count}))
    return out


@router.post("", response_model=GroupOut, status_code=201)
def create_group(
    request: Request,
    body: GroupIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_roles(user, ADMIN_ROLES)
    if db.query(DeviceGroup).filter(DeviceGroup.name == body.name).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "El grupo ya existe")
    row = DeviceGroup(name=body.name, description=body.description)
    db.add(row)
    db.flush()
    write_audit(db, user=user, ip=client_ip(request), action="group_create", target_type="group", target_id=row.id)
    return GroupOut.model_validate(row).model_copy(update={"device_count": 0})


@router.patch("/{group_id}", response_model=GroupOut)
def update_group(
    group_id: str,
    request: Request,
    body: GroupIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_roles(user, ADMIN_ROLES)
    row = db.get(DeviceGroup, group_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Grupo no encontrado")
    row.name = body.name
    row.description = body.description
    write_audit(db, user=user, ip=client_ip(request), action="group_update", target_type="group", target_id=row.id)
    count = db.query(DeviceGroupMember).filter(DeviceGroupMember.group_id == row.id).count()
    return GroupOut.model_validate(row).model_copy(update={"device_count": count})


@router.delete("/{group_id}")
def delete_group(
    group_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_roles(user, ADMIN_ROLES)
    row = db.get(DeviceGroup, group_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Grupo no encontrado")
    db.delete(row)
    write_audit(db, user=user, ip=client_ip(request), action="group_delete", target_type="group", target_id=group_id)
    return {"ok": True}
