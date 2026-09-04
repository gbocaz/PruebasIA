from enum import Enum


class RoleName(str, Enum):
    SUPERADMIN = "superadmin"
    ADMINISTRADOR_TIC = "administrador_tic"
    SOPORTE = "soporte"
    VISUALIZADOR = "visualizador"
    DIRECTIVO = "directivo"


class DeviceStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    ADVERTENCIA = "advertencia"
    CRITICO = "critico"
    EXCLUIDO = "excluido"
    MANTENIMIENTO = "mantenimiento"


class SoftwareCategory(str, Enum):
    AUTORIZADO = "autorizado"
    NO_AUTORIZADO = "no_autorizado"
    OBLIGATORIO = "obligatorio"
    OPCIONAL = "opcional"
    IGNORAR = "ignorar"


class AlertLevel(str, Enum):
    INFO = "info"
    ADVERTENCIA = "advertencia"
    IMPORTANTE = "importante"
    CRITICO = "critico"


class InstallStatus(str, Enum):
    PENDIENTE = "pendiente"
    DESCARGANDO = "descargando"
    INSTALANDO = "instalando"
    INSTALADO = "instalado"
    ERROR = "error"


class TaskType(str, Enum):
    COLLECT_INVENTORY = "collect_inventory"
    INSTALL_PACKAGE = "install_package"
    RESTART_AGENT = "restart_agent"
    UPDATE_AGENT = "update_agent"


class TaskStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class OsFamily(str, Enum):
    WINDOWS = "windows"
    LINUX = "linux"
    OTHER = "other"
