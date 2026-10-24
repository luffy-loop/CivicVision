"""Add assignment tracking and repair completion evidence."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "20261024_03"
down_revision = "20261024_02"
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    columns = {column["name"] for column in inspect(bind).get_columns("reports")}
    with op.batch_alter_table("reports") as batch:
        if "assigned_team" not in columns:
            batch.add_column(sa.Column("assigned_team", sa.String(length=120), nullable=True))
        if "assigned_at" not in columns:
            batch.add_column(sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=True))
        if "assigned_by" not in columns:
            batch.add_column(sa.Column("assigned_by", sa.String(length=120), nullable=True))
    if "resolution_evidence" not in inspect(bind).get_table_names():
        from app.models import ResolutionEvidence
        ResolutionEvidence.__table__.create(bind, checkfirst=True)

def downgrade():
    op.drop_table("resolution_evidence")
    with op.batch_alter_table("reports") as batch:
        batch.drop_column("assigned_by")
        batch.drop_column("assigned_at")
        batch.drop_column("assigned_team")
