from alembic import op
import sqlalchemy as sa

revision = "0001_mvp"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # El MVP crea el esquema con SQLAlchemy metadata.create_all al arrancar.
    # Esta revisión deja constancia de la línea base para migraciones futuras:
    # alembic revision --autogenerate -m "descripcion"
    pass


def downgrade() -> None:
    pass
