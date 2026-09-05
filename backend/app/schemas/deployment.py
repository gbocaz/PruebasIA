from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AgentReleaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    version: str
    os_family: str
    architecture: str
    sha256: str
    original_filename: str
    size_bytes: int
    notes: str
    created_at: datetime


class DeploymentKitCreate(BaseModel):
    release_id: str
    label: str = Field(min_length=1, max_length=128)
    public_server_url: str = Field(min_length=1, max_length=512)
    group_id: str | None = None
    max_uses: int = Field(default=1, ge=1, le=10000)
    expires_hours: int = Field(default=24, ge=1, le=720)


class DeploymentKitOut(BaseModel):
    kit_id: str
    release_id: str
    release_version: str
    os_family: str
    architecture: str
    sha256: str
    token: str
    token_prefix: str
    expires_at: datetime
    install_script: str
    filename: str
    instructions: list[str]
