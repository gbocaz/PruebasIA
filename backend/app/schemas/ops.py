from datetime import datetime

from pydantic import BaseModel, Field

from app.enums import DeviceStatus, OsFamily, SoftwareCategory
from app.schemas.auth import ORMModel


class DeviceOut(ORMModel):
    id: str
    hostname: str
    display_name: str
    os_family: str
    os_name: str
    os_version: str
    architecture: str
    ip_address: str
    mac_address: str
    logged_user: str
    cpu_model: str
    cpu_percent: float
    ram_total_mb: int
    ram_used_mb: int
    disk_total_gb: float
    disk_used_gb: float
    uptime_seconds: int
    agent_version: str
    status: str
    last_seen_at: datetime | None
    enrolled_at: datetime
    notes: str
    exclude_wallpaper: bool
    exclude_chrome: bool
    exclude_software: bool
    exclude_traffic: bool
    exclude_ai: bool
    groups: list[str] = []


class DeviceUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=255)
    notes: str | None = None
    status: DeviceStatus | None = None
    exclude_wallpaper: bool | None = None
    exclude_chrome: bool | None = None
    exclude_software: bool | None = None
    exclude_traffic: bool | None = None
    exclude_ai: bool | None = None
    group_ids: list[str] | None = None


class DeviceActionRequest(BaseModel):
    action: str = Field(pattern="^(collect_inventory|restart_agent)$")
    confirm: bool = False


class GroupIn(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str = ""


class GroupOut(ORMModel):
    id: str
    name: str
    description: str
    device_count: int = 0
    created_at: datetime


class SoftwareOut(ORMModel):
    id: str
    name: str
    publisher: str
    category: str
    install_count: int = 0


class SoftwareUpdate(BaseModel):
    category: SoftwareCategory


class DeviceSoftwareOut(BaseModel):
    software_id: str
    name: str
    publisher: str
    version: str
    category: str
    detected_at: datetime
    last_seen_at: datetime


class PackageOut(ORMModel):
    id: str
    name: str
    version: str
    os_family: str
    architecture: str
    sha256: str
    install_command: str
    original_filename: str
    size_bytes: int
    created_by: str | None
    created_at: datetime
    notes: str


class InstallCreate(BaseModel):
    package_id: str
    target_type: str = Field(pattern="^(device|group|all)$")
    target_id: str = ""
    confirm: bool = False
    notes: str = ""


class AlertOut(ORMModel):
    id: str
    level: str
    title: str
    message: str
    device_id: str | None
    acknowledged: bool
    created_at: datetime


class AuditOut(ORMModel):
    id: str
    created_at: datetime
    username: str
    ip_address: str
    action: str
    target_type: str
    target_id: str
    result: str
    details: str


class EnrollmentTokenCreate(BaseModel):
    label: str = Field(default="", max_length=128)
    max_uses: int = Field(default=10, ge=1, le=10000)
    expires_hours: int | None = Field(default=72, ge=1, le=24 * 30)
    group_id: str | None = None


class EnrollmentTokenOut(BaseModel):
    id: str
    label: str
    token: str | None = None
    token_prefix: str
    max_uses: int
    use_count: int
    expires_at: datetime | None
    group_id: str | None
    created_at: datetime


class InterfaceOut(ORMModel):
    name: str
    mac: str
    ipv4: str
    ipv6: str
    is_up: bool
    speed_mbps: int
    bytes_sent: int
    bytes_recv: int


class MetricOut(ORMModel):
    collected_at: datetime
    cpu_percent: float
    ram_used_mb: int
    ram_total_mb: int
    disk_used_gb: float
    disk_total_gb: float
    bytes_sent: int
    bytes_recv: int


class EventOut(ORMModel):
    id: str
    type: str
    message: str
    created_at: datetime


class HeartbeatIn(BaseModel):
    hostname: str
    os_family: OsFamily
    os_name: str = ""
    os_version: str = ""
    architecture: str = ""
    ip_address: str = ""
    mac_address: str = ""
    logged_user: str = ""
    cpu_model: str = ""
    cpu_percent: float = 0
    ram_total_mb: int = 0
    ram_used_mb: int = 0
    disk_total_gb: float = 0
    disk_used_gb: float = 0
    uptime_seconds: int = 0
    agent_version: str = ""
    bytes_sent: int = 0
    bytes_recv: int = 0
    interfaces: list[InterfaceOut] = []


class InventoryItemIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    version: str = ""
    publisher: str = ""


class InventoryIn(BaseModel):
    software: list[InventoryItemIn] = []
    interfaces: list[InterfaceOut] = []


class EnrollIn(BaseModel):
    token: str
    hostname: str
    os_family: OsFamily
    os_name: str = ""
    os_version: str = ""
    architecture: str = ""
    agent_version: str = ""


class TaskResultIn(BaseModel):
    task_id: str
    success: bool
    message: str = ""
    extra_json: str = ""
