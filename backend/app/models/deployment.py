from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.user import EnrollmentToken, new_id, utcnow


class AgentRelease(Base):
    __tablename__ = "agent_releases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    version: Mapped[str] = mapped_column(String(32), index=True)
    os_family: Mapped[str] = mapped_column(String(16), index=True)
    architecture: Mapped[str] = mapped_column(String(32), index=True)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    storage_path: Mapped[str] = mapped_column(String(512))
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AgentDeploymentKit(Base):
    __tablename__ = "agent_deployment_kits"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    release_id: Mapped[str] = mapped_column(ForeignKey("agent_releases.id", ondelete="CASCADE"), index=True)
    enrollment_token_id: Mapped[str] = mapped_column(
        ForeignKey("enrollment_tokens.id", ondelete="CASCADE"), unique=True, index=True
    )
    label: Mapped[str] = mapped_column(String(128))
    public_server_url: Mapped[str] = mapped_column(String(512))
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    release: Mapped[AgentRelease] = relationship()
    enrollment_token: Mapped[EnrollmentToken] = relationship()
