from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.user import new_id, utcnow


class NetworkSite(Base):
    __tablename__ = "network_sites"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    location: Mapped[str] = mapped_column(String(255), default="")
    cidrs_json: Mapped[str] = mapped_column(Text, default="[]")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    max_hosts_per_scan: Mapped[int] = mapped_column(Integer, default=4096)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    collectors: Mapped[list["NetworkCollector"]] = relationship(back_populates="site", cascade="all, delete-orphan")
    credentials: Mapped[list["NetworkCredential"]] = relationship(back_populates="site", cascade="all, delete-orphan")


class NetworkCollector(Base):
    __tablename__ = "network_collectors"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    site_id: Mapped[str] = mapped_column(ForeignKey("network_sites.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(128))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    token_prefix: Mapped[str] = mapped_column(String(12), index=True)
    hostname: Mapped[str] = mapped_column(String(255), default="")
    version: Mapped[str] = mapped_column(String(32), default="")
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    site: Mapped[NetworkSite] = relationship(back_populates="collectors")


class NetworkCredential(Base):
    __tablename__ = "network_credentials"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    site_id: Mapped[str] = mapped_column(ForeignKey("network_sites.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(128))
    kind: Mapped[str] = mapped_column(String(32), index=True)  # snmp_v3 | snmp_v2c
    username: Mapped[str] = mapped_column(String(128), default="")
    secret_encrypted: Mapped[str] = mapped_column(Text, default="")
    auth_protocol: Mapped[str] = mapped_column(String(16), default="SHA")
    privacy_protocol: Mapped[str] = mapped_column(String(16), default="AES")
    privacy_secret_encrypted: Mapped[str] = mapped_column(Text, default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    site: Mapped[NetworkSite] = relationship(back_populates="credentials")


class NetworkScanJob(Base):
    __tablename__ = "network_scan_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    site_id: Mapped[str] = mapped_column(ForeignKey("network_sites.id", ondelete="CASCADE"), index=True)
    collector_id: Mapped[str | None] = mapped_column(ForeignKey("network_collectors.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="pending", index=True)
    methods_json: Mapped[str] = mapped_column(Text, default='["tcp","arp","snmp"]')
    requested_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    result_count: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str] = mapped_column(Text, default="")


class NetworkDevice(Base):
    __tablename__ = "network_devices"
    __table_args__ = (UniqueConstraint("site_id", "identity_key", name="uq_network_device_identity"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    site_id: Mapped[str] = mapped_column(ForeignKey("network_sites.id", ondelete="CASCADE"), index=True)
    managed_device_id: Mapped[str | None] = mapped_column(
        ForeignKey("devices.id", ondelete="SET NULL"), nullable=True, index=True
    )
    identity_key: Mapped[str] = mapped_column(String(255))
    ip_address: Mapped[str] = mapped_column(String(64), default="", index=True)
    mac_address: Mapped[str] = mapped_column(String(32), default="", index=True)
    hostname: Mapped[str] = mapped_column(String(255), default="", index=True)
    vendor: Mapped[str] = mapped_column(String(128), default="Desconocido", index=True)
    model: Mapped[str] = mapped_column(String(255), default="")
    serial_number: Mapped[str] = mapped_column(String(128), default="")
    device_type: Mapped[str] = mapped_column(String(32), default="desconocido", index=True)
    os_name: Mapped[str] = mapped_column(String(128), default="")
    status: Mapped[str] = mapped_column(String(24), default="online", index=True)
    discovery_source: Mapped[str] = mapped_column(String(64), default="")
    sys_name: Mapped[str] = mapped_column(String(255), default="")
    sys_description: Mapped[str] = mapped_column(Text, default="")
    sys_object_id: Mapped[str] = mapped_column(String(255), default="")
    open_ports_json: Mapped[str] = mapped_column(Text, default="[]")
    remote_services_json: Mapped[str] = mapped_column(Text, default="[]")
    management_url: Mapped[str] = mapped_column(String(512), default="")
    switch_port: Mapped[str] = mapped_column(String(128), default="")
    vlan: Mapped[str] = mapped_column(String(64), default="")
    ssid: Mapped[str] = mapped_column(String(128), default="")
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class NetworkLink(Base):
    __tablename__ = "network_links"
    __table_args__ = (
        UniqueConstraint(
            "site_id",
            "source_identity",
            "target_identity",
            "source_port",
            name="uq_network_link",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    site_id: Mapped[str] = mapped_column(ForeignKey("network_sites.id", ondelete="CASCADE"), index=True)
    source_identity: Mapped[str] = mapped_column(String(255))
    target_identity: Mapped[str] = mapped_column(String(255))
    source_port: Mapped[str] = mapped_column(String(128), default="")
    target_port: Mapped[str] = mapped_column(String(128), default="")
    protocol: Mapped[str] = mapped_column(String(16), default="lldp")
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
