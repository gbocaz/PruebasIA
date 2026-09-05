import ipaddress

from fastapi import HTTPException, Request, status

from app.config import get_settings
from app.enums import RoleName
from app.models.user import User

# Lectura amplia. Escritura de inventario/políticas. Acciones de soporte. Solo indicadores.
READ_ROLES = {r.value for r in RoleName}
ADMIN_ROLES = {RoleName.SUPERADMIN.value, RoleName.ADMINISTRADOR_TIC.value}
SUPPORT_ACTIONS = ADMIN_ROLES | {RoleName.SOPORTE.value}
USER_ADMIN = {RoleName.SUPERADMIN.value}
AUDIT_ROLES = ADMIN_ROLES | {RoleName.DIRECTIVO.value}


def require_roles(user: User, allowed: set[str]) -> None:
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Usuario desactivado")
    if user.role not in allowed:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No autorizado para esta acción")


def client_ip(request: Request) -> str:
    direct = request.client.host if request.client else ""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded and _trusted_proxy(direct):
        return forwarded.split(",")[0].strip()
    return direct


def _trusted_proxy(address: str) -> bool:
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return False
    for raw in get_settings().trusted_proxy_list:
        try:
            if ip in ipaddress.ip_network(raw, strict=False):
                return True
        except ValueError:
            continue
    return False
