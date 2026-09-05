from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class NetworkSiteIn(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str = Field(default="", max_length=4000)
    location: str = Field(default="", max_length=255)
    cidrs: list[str] = Field(min_length=1, max_length=64)
    enabled: bool = True
    max_hosts_per_scan: int = Field(default=4096, ge=1, le=65536)

    @field_validator("cidrs")
    @classmethod
    def unique_cidrs(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(item.strip() for item in value if item.strip()))


class NetworkSiteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str
    location: str
    cidrs: list[str]
    enabled: bool
    max_hosts_per_scan: int
    collector_count: int = 0
    collectors_online: int = 0
    device_count: int = 0
    created_at: datetime


class CollectorCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)


class CollectorOut(BaseModel):
    id: str
    site_id: str
    name: str
    token: str | None = None
    token_prefix: str
    hostname: str
    version: str
    online: bool
    last_seen_at: datetime | None
    revoked: bool
    created_at: datetime


class CredentialCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    kind: str = Field(pattern="^(snmp_v3|snmp_v2c)$")
    username: str = Field(default="", max_length=128)
    secret: str = Field(min_length=1, max_length=512)
    auth_protocol: str = Field(default="SHA", pattern="^(MD5|SHA|SHA224|SHA256|SHA384|SHA512)$")
    privacy_protocol: str = Field(default="AES", pattern="^(NONE|DES|AES|AES192|AES256)$")
    privacy_secret: str = Field(default="", max_length=512)
    enabled: bool = True


class CredentialOut(BaseModel):
    id: str
    site_id: str
    name: str
    kind: str
    username: str
    auth_protocol: str
    privacy_protocol: str
    enabled: bool
    created_at: datetime


class ScanCreate(BaseModel):
    site_id: str
    methods: list[str] = ["tcp", "arp", "snmp"]
    confirm: bool = False

    @field_validator("methods")
    @classmethod
    def supported_methods(cls, value: list[str]) -> list[str]:
        supported = {"tcp", "arp", "snmp"}
        cleaned = list(dict.fromkeys(value))
        if not cleaned or any(item not in supported for item in cleaned):
            raise ValueError("Métodos permitidos: tcp, arp, snmp")
        return cleaned


class ScanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    site_id: str
    collector_id: str | None
    status: str
    methods: list[str]
    requested_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    result_count: int
    error: str


class NetworkDeviceOut(BaseModel):
    id: str
    site_id: str
    ip_address: str
    mac_address: str
    hostname: str
    vendor: str
    model: str
    serial_number: str
    device_type: str
    os_name: str
    status: str
    discovery_source: str
    sys_name: str
    sys_description: str
    sys_object_id: str
    open_ports: list[int]
    remote_services: list[str]
    management_url: str
    switch_port: str
    vlan: str
    ssid: str
    first_seen_at: datetime
    last_seen_at: datetime


class CollectorHeartbeat(BaseModel):
    hostname: str = Field(max_length=255)
    version: str = Field(max_length=32)


class DiscoveredDevice(BaseModel):
    identity_key: str = Field(min_length=1, max_length=255)
    ip_address: str = Field(default="", max_length=64)
    mac_address: str = Field(default="", max_length=32)
    hostname: str = Field(default="", max_length=255)
    vendor: str = Field(default="Desconocido", max_length=128)
    model: str = Field(default="", max_length=255)
    serial_number: str = Field(default="", max_length=128)
    device_type: str = Field(default="desconocido", max_length=32)
    os_name: str = Field(default="", max_length=128)
    status: str = Field(default="online", pattern="^(online|offline|advertencia)$")
    discovery_source: str = Field(default="", max_length=64)
    sys_name: str = Field(default="", max_length=255)
    sys_description: str = Field(default="", max_length=4000)
    sys_object_id: str = Field(default="", max_length=255)
    open_ports: list[int] = []
    remote_services: list[str] = []
    management_url: str = Field(default="", max_length=512)
    switch_port: str = Field(default="", max_length=128)
    vlan: str = Field(default="", max_length=64)
    ssid: str = Field(default="", max_length=128)


class DiscoveredLink(BaseModel):
    source_identity: str = Field(min_length=1, max_length=255)
    target_identity: str = Field(min_length=1, max_length=255)
    source_port: str = Field(default="", max_length=128)
    target_port: str = Field(default="", max_length=128)
    protocol: str = Field(default="lldp", pattern="^(lldp|cdp|bridge|manual)$")


class ScanResultIn(BaseModel):
    devices: list[DiscoveredDevice] = Field(default=[], max_length=65536)
    links: list[DiscoveredLink] = Field(default=[], max_length=100000)
    error: str = Field(default="", max_length=4000)


class RemoteSessionRequest(BaseModel):
    protocol: str = Field(pattern="^(rdp|vnc|ssh|http|https)$")
    username: str = Field(default="", max_length=128)
    confirm: bool = False
