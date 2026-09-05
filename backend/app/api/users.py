from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.enums import RoleName
from app.models.user import User
from app.schemas.auth import UserCreate, UserOut, UserUpdate
from app.security.audit import write_audit
from app.security.deps import get_current_user
from app.security.passwords import hash_password
from app.security.rbac import USER_ADMIN, client_ip, require_roles

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_roles(user, USER_ADMIN | {RoleName.ADMINISTRADOR_TIC.value, RoleName.DIRECTIVO.value})
    return db.query(User).order_by(User.username).all()


@router.post("", response_model=UserOut, status_code=201)
def create_user(
    request: Request,
    body: UserCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_roles(user, USER_ADMIN)
    if db.query(User).filter((User.username == body.username) | (User.email == body.email)).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Usuario o correo ya existe")
    row = User(
        username=body.username,
        email=str(body.email),
        full_name=body.full_name,
        password_hash=hash_password(body.password),
        role=body.role.value,
    )
    db.add(row)
    db.flush()
    write_audit(db, user=user, ip=client_ip(request), action="user_create", target_type="user", target_id=row.id)
    return row


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: str,
    request: Request,
    body: UserUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_roles(user, USER_ADMIN)
    row = db.get(User, user_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")
    data = body.model_dump(exclude_unset=True)
    if "password" in data and data["password"]:
        row.password_hash = hash_password(data.pop("password"))
    if "role" in data and data["role"] is not None:
        row.role = data.pop("role").value
    if "email" in data and data["email"] is not None:
        row.email = str(data.pop("email"))
    for key, value in data.items():
        setattr(row, key, value)
    write_audit(db, user=user, ip=client_ip(request), action="user_update", target_type="user", target_id=row.id)
    return row
