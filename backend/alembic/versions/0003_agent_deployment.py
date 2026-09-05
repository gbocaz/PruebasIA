"""Add dedicated agent releases, deployment kits and managed-device link."""

import sqlalchemy as sa
from alembic import op

from app.models.deployment import AgentDeploymentKit, AgentRelease

revision = "0003_agent_deployment"
down_revision = "0002_network_discovery"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    AgentRelease.__table__.create(bind, checkfirst=True)
    AgentDeploymentKit.__table__.create(bind, checkfirst=True)
    columns = {column["name"] for column in sa.inspect(bind).get_columns("network_devices")}
    if "managed_device_id" not in columns:
        op.add_column(
            "network_devices",
            sa.Column(
                "managed_device_id",
                sa.String(length=36),
                sa.ForeignKey("devices.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )
        op.create_index(
            "ix_network_devices_managed_device_id",
            "network_devices",
            ["managed_device_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("network_devices")}
    if "managed_device_id" in columns:
        indexes = {index["name"] for index in sa.inspect(bind).get_indexes("network_devices")}
        if "ix_network_devices_managed_device_id" in indexes:
            op.drop_index("ix_network_devices_managed_device_id", table_name="network_devices")
        op.drop_column("network_devices", "managed_device_id")
    AgentDeploymentKit.__table__.drop(bind, checkfirst=True)
    AgentRelease.__table__.drop(bind, checkfirst=True)
