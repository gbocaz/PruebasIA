"""Add vendor-neutral network discovery tables."""

from alembic import op

from app.models.network import (
    NetworkCollector,
    NetworkCredential,
    NetworkDevice,
    NetworkLink,
    NetworkScanJob,
    NetworkSite,
)

revision = "0002_network_discovery"
down_revision = "0001_mvp"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    for table in (
        NetworkSite.__table__,
        NetworkCollector.__table__,
        NetworkCredential.__table__,
        NetworkScanJob.__table__,
        NetworkDevice.__table__,
        NetworkLink.__table__,
    ):
        table.create(bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    for table in (
        NetworkLink.__table__,
        NetworkDevice.__table__,
        NetworkScanJob.__table__,
        NetworkCredential.__table__,
        NetworkCollector.__table__,
        NetworkSite.__table__,
    ):
        table.drop(bind, checkfirst=True)
