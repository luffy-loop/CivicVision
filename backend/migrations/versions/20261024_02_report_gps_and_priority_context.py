"""Persist GPS capture time and transparent priority rationale."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "20261024_02"
down_revision = "20261024_01"
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    columns = {column["name"] for column in inspect(bind).get_columns("reports")}
    with op.batch_alter_table("reports") as batch:
        if "location_captured_at" not in columns:
            batch.add_column(sa.Column("location_captured_at", sa.DateTime(timezone=True), nullable=True))
        if "priority_reason" not in columns:
            batch.add_column(sa.Column("priority_reason", sa.Text(), nullable=True))

def downgrade():
    with op.batch_alter_table("reports") as batch:
        batch.drop_column("priority_reason")
        batch.drop_column("location_captured_at")
