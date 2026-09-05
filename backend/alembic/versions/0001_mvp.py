"""Create the MVP schema baseline."""

from alembic import op

from app.database import Base
from app.models import *  # noqa: F401,F403

revision = "0001_mvp"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    for name in TABLES:
        Base.metadata.tables[name].create(bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    for name in reversed(TABLES):
        Base.metadata.tables[name].drop(bind, checkfirst=True)


TABLES = [
    "users",
    "refresh_tokens",
    "device_groups",
    "enrollment_tokens",
    "devices",
    "device_group_members",
    "agents",
    "network_interfaces",
    "device_metrics",
    "agent_tasks",
    "events",
    "software",
    "device_software",
    "software_packages",
    "install_jobs",
    "install_job_devices",
    "alerts",
    "audit_logs",
    "system_settings",
]
