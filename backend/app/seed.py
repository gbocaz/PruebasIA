from sqlalchemy.orm import Session

from app.config import get_settings
from app.enums import RoleName
from app.models.device import DeviceGroup
from app.models.ops import SystemSetting
from app.models.user import User
from app.security.passwords import hash_password

DEFAULT_GROUPS = [
    ("Laboratorio 1", "Sala informática 1"),
    ("Laboratorio 2", "Sala informática 2"),
    ("Profesores", "Equipos de docentes"),
    ("Administración", "Equipos administrativos"),
    ("Biblioteca", "Equipos de biblioteca"),
    ("Portátiles", "Equipos portátiles"),
    ("Servidores", "Servidores institucionales"),
    ("Equipos especiales", "Excepciones y casos puntuales"),
]


def seed_if_empty(db: Session) -> None:
    settings = get_settings()
    if db.query(User).count() == 0:
        db.add(
            User(
                username=settings.bootstrap_admin_username,
                email=settings.bootstrap_admin_email,
                full_name="Administrador inicial",
                password_hash=hash_password(settings.bootstrap_admin_password),
                role=RoleName.SUPERADMIN.value,
            )
        )
    if db.query(DeviceGroup).count() == 0:
        for name, description in DEFAULT_GROUPS:
            db.add(DeviceGroup(name=name, description=description))
    if db.get(SystemSetting, "heartbeat_seconds") is None:
        db.add(SystemSetting(key="heartbeat_seconds", value=str(settings.default_heartbeat_seconds)))
        db.add(SystemSetting(key="offline_factor", value=str(settings.heartbeat_offline_factor)))
    db.commit()
