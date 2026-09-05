import json
from datetime import timedelta

from sqlalchemy.orm import Session

from app.enums import TaskStatus, TaskType
from app.models.device import Agent, AgentTask, Device
from app.security.crypto import decrypt_secret
from app.security.tokens import canonical_iso, sign_task, utcnow


def create_task(
    db: Session,
    device: Device,
    task_type: TaskType,
    params: dict,
    ttl_hours: int = 12,
) -> AgentTask:
    agent: Agent | None = device.agent
    if agent is None or agent.revoked:
        raise ValueError("El equipo no tiene agente activo")
    expires = utcnow() + timedelta(hours=ttl_hours)
    expires_iso = canonical_iso(expires)
    task = AgentTask(
        device_id=device.id,
        type=task_type.value,
        payload_json=json.dumps(params, ensure_ascii=False),
        status=TaskStatus.PENDING.value,
        expires_at=expires,
    )
    db.add(task)
    db.flush()
    secret = decrypt_secret(agent.hmac_secret_encrypted)
    task.signature = sign_task(secret, task.id, device.id, task.type, expires_iso)
    return task


def pending_tasks(db: Session, device_id: str) -> list[AgentTask]:
    now = utcnow()
    rows = (
        db.query(AgentTask)
        .filter(
            AgentTask.device_id == device_id,
            AgentTask.status.in_([TaskStatus.PENDING.value, TaskStatus.SENT.value]),
            AgentTask.expires_at > now,
        )
        .order_by(AgentTask.created_at.asc())
        .all()
    )
    for row in rows:
        if row.status == TaskStatus.PENDING.value:
            row.status = TaskStatus.SENT.value
    expired = (
        db.query(AgentTask)
        .filter(
            AgentTask.device_id == device_id,
            AgentTask.status.in_([TaskStatus.PENDING.value, TaskStatus.SENT.value]),
            AgentTask.expires_at <= now,
        )
        .all()
    )
    for row in expired:
        row.status = TaskStatus.EXPIRED.value
    return rows
