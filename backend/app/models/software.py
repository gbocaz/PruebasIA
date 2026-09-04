from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.enums import SoftwareCategory
from app.models.user import new_id, utcnow


class Software(Base):
    __tablename__ = "software"
    __table_args__ = (UniqueConstraint("name_normalized", "publisher_normalized", name="uq_software_name_pub"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(255), index=True)
    name_normalized: Mapped[str] = mapped_column(String(255), index=True)
    publisher: Mapped[str] = mapped_column(String(255), default="")
    publisher_normalized: Mapped[str] = mapped_column(String(255), default="")
    category: Mapped[str] = mapped_column(String(32), default=SoftwareCategory.OPCIONAL.value, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class DeviceSoftware(Base):
    __tablename__ = "device_software"
    __table_args__ = (UniqueConstraint("device_id", "software_id", name="uq_device_software"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), index=True)
    software_id: Mapped[str] = mapped_column(ForeignKey("software.id", ondelete="CASCADE"), index=True)
    version: Mapped[str] = mapped_column(String(128), default="")
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    software: Mapped[Software] = relationship()


class SoftwarePackage(Base):
    __tablename__ = "software_packages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(255), index=True)
    version: Mapped[str] = mapped_column(String(64), default="")
    os_family: Mapped[str] = mapped_column(String(16), index=True)
    architecture: Mapped[str] = mapped_column(String(32), default="any")
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    install_command: Mapped[str] = mapped_column(Text)
    original_filename: Mapped[str] = mapped_column(String(255))
    storage_path: Mapped[str] = mapped_column(String(512))
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    notes: Mapped[str] = mapped_column(Text, default="")


class InstallJob(Base):
    __tablename__ = "install_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    package_id: Mapped[str] = mapped_column(ForeignKey("software_packages.id"), index=True)
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    target_type: Mapped[str] = mapped_column(String(32))  # device | group | all
    target_id: Mapped[str] = mapped_column(String(36), default="")
    confirm: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    notes: Mapped[str] = mapped_column(Text, default="")

    package: Mapped[SoftwarePackage] = relationship()
    devices: Mapped[list["InstallJobDevice"]] = relationship(back_populates="job", cascade="all, delete-orphan")


class InstallJobDevice(Base):
    __tablename__ = "install_job_devices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    job_id: Mapped[str] = mapped_column(ForeignKey("install_jobs.id", ondelete="CASCADE"), index=True)
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), index=True)
    task_id: Mapped[str | None] = mapped_column(ForeignKey("agent_tasks.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="pendiente", index=True)
    message: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    job: Mapped[InstallJob] = relationship(back_populates="devices")
