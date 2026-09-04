from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.enums import DeviceStatus
from app.models.user import new_id, utcnow


class DeviceGroup(Base):
    __tablename__ = "device_groups"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    members: Mapped[list["DeviceGroupMember"]] = relationship(back_populates="group", cascade="all, delete-orphan")


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    hostname: Mapped[str] = mapped_column(String(255), index=True)
    display_name: Mapped[str] = mapped_column(String(255), default="")
    os_family: Mapped[str] = mapped_column(String(16), index=True)
    os_name: Mapped[str] = mapped_column(String(128), default="")
    os_version: Mapped[str] = mapped_column(String(128), default="")
    architecture: Mapped[str] = mapped_column(String(32), default="")
    ip_address: Mapped[str] = mapped_column(String(64), default="", index=True)
    mac_address: Mapped[str] = mapped_column(String(32), default="", index=True)
    logged_user: Mapped[str] = mapped_column(String(128), default="")
    cpu_model: Mapped[str] = mapped_column(String(255), default="")
    cpu_percent: Mapped[float] = mapped_column(Float, default=0)
    ram_total_mb: Mapped[int] = mapped_column(Integer, default=0)
    ram_used_mb: Mapped[int] = mapped_column(Integer, default=0)
    disk_total_gb: Mapped[float] = mapped_column(Float, default=0)
    disk_used_gb: Mapped[float] = mapped_column(Float, default=0)
    uptime_seconds: Mapped[int] = mapped_column(Integer, default=0)
    agent_version: Mapped[str] = mapped_column(String(32), default="")
    status: Mapped[str] = mapped_column(String(24), default=DeviceStatus.OFFLINE.value, index=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    enrolled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    notes: Mapped[str] = mapped_column(Text, default="")
    exclude_wallpaper: Mapped[bool] = mapped_column(Boolean, default=False)
    exclude_chrome: Mapped[bool] = mapped_column(Boolean, default=False)
    exclude_software: Mapped[bool] = mapped_column(Boolean, default=False)
    exclude_traffic: Mapped[bool] = mapped_column(Boolean, default=False)
    exclude_ai: Mapped[bool] = mapped_column(Boolean, default=False)

    agent: Mapped["Agent | None"] = relationship(back_populates="device", uselist=False)
    group_links: Mapped[list["DeviceGroupMember"]] = relationship(back_populates="device", cascade="all, delete-orphan")
    interfaces: Mapped[list["NetworkInterface"]] = relationship(back_populates="device", cascade="all, delete-orphan")


class DeviceGroupMember(Base):
    __tablename__ = "device_group_members"
    __table_args__ = (UniqueConstraint("device_id", "group_id", name="uq_device_group"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), index=True)
    group_id: Mapped[str] = mapped_column(ForeignKey("device_groups.id", ondelete="CASCADE"), index=True)

    device: Mapped[Device] = relationship(back_populates="group_links")
    group: Mapped[DeviceGroup] = relationship(back_populates="members")


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), unique=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    hmac_secret_encrypted: Mapped[str] = mapped_column(Text)
    version: Mapped[str] = mapped_column(String(32), default="")
    heartbeat_interval_seconds: Mapped[int] = mapped_column(Integer, default=60)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    enrolled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    device: Mapped[Device] = relationship(back_populates="agent")


class NetworkInterface(Base):
    __tablename__ = "network_interfaces"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(128), default="")
    mac: Mapped[str] = mapped_column(String(32), default="")
    ipv4: Mapped[str] = mapped_column(String(64), default="")
    ipv6: Mapped[str] = mapped_column(String(64), default="")
    is_up: Mapped[bool] = mapped_column(Boolean, default=True)
    speed_mbps: Mapped[int] = mapped_column(Integer, default=0)
    bytes_sent: Mapped[int] = mapped_column(Integer, default=0)
    bytes_recv: Mapped[int] = mapped_column(Integer, default=0)

    device: Mapped[Device] = relationship(back_populates="interfaces")


class DeviceMetric(Base):
    __tablename__ = "device_metrics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), index=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    cpu_percent: Mapped[float] = mapped_column(Float, default=0)
    ram_used_mb: Mapped[int] = mapped_column(Integer, default=0)
    ram_total_mb: Mapped[int] = mapped_column(Integer, default=0)
    disk_used_gb: Mapped[float] = mapped_column(Float, default=0)
    disk_total_gb: Mapped[float] = mapped_column(Float, default=0)
    bytes_sent: Mapped[int] = mapped_column(Integer, default=0)
    bytes_recv: Mapped[int] = mapped_column(Integer, default=0)


class AgentTask(Base):
    __tablename__ = "agent_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(64), index=True)
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    signature: Mapped[str] = mapped_column(String(128), default="")
    status: Mapped[str] = mapped_column(String(24), default="pending", index=True)
    result_json: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DeviceEvent(Base):
    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    device_id: Mapped[str | None] = mapped_column(ForeignKey("devices.id", ondelete="SET NULL"), nullable=True, index=True)
    type: Mapped[str] = mapped_column(String(64), index=True)
    message: Mapped[str] = mapped_column(Text, default="")
    extra_json: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
