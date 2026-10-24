"""Add citizen tracking, inference metadata, location accuracy and audit actor."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "20261024_01"
down_revision = None
branch_labels = None
depends_on = None

def _ensure_base_tables(bind):
    inspector = inspect(bind)
    if "reports" not in inspector.get_table_names():
        from app.models import Report, StatusEvent
        Report.__table__.create(bind, checkfirst=True)
        StatusEvent.__table__.create(bind, checkfirst=True)
    elif "status_events" not in inspector.get_table_names():
        from app.models import StatusEvent
        StatusEvent.__table__.create(bind, checkfirst=True)

def upgrade():
    bind = op.get_bind()
    _ensure_base_tables(bind)
    inspector = inspect(bind)
    report_columns = {column["name"] for column in inspector.get_columns("reports")}
    additions = [
        ("model_version", sa.String(length=100)),
        ("priority_reason", sa.Text()),
        ("inference_ms", sa.Float()),
        ("detections_json", sa.Text()),
        ("location_accuracy_m", sa.Float()),
        ("location_captured_at", sa.DateTime(timezone=True)),
        ("tracking_token_hash", sa.String(length=64)),
        ("idempotency_key_hash", sa.String(length=64)),
    ]
    with op.batch_alter_table("reports") as batch:
        for name, column_type in additions:
            if name not in report_columns:
                batch.add_column(sa.Column(name, column_type, nullable=True))
    inspector = inspect(bind)
    status_columns = {column["name"] for column in inspector.get_columns("status_events")}
    if "actor" not in status_columns:
        with op.batch_alter_table("status_events") as batch:
            batch.add_column(sa.Column("actor", sa.String(length=120), nullable=True))
    indexes = {index["name"] for index in inspect(bind).get_indexes("reports")}
    if "ix_reports_tracking_token_hash" not in indexes:
        op.create_index("ix_reports_tracking_token_hash", "reports", ["tracking_token_hash"], unique=True)
    indexes = {index["name"] for index in inspect(bind).get_indexes("reports")}
    if "ix_reports_idempotency_key_hash" not in indexes:
        op.create_index("ix_reports_idempotency_key_hash", "reports", ["idempotency_key_hash"], unique=True)

def downgrade():
    op.drop_index("ix_reports_idempotency_key_hash", table_name="reports")
    op.drop_index("ix_reports_tracking_token_hash", table_name="reports")
    with op.batch_alter_table("status_events") as batch:
        batch.drop_column("actor")
    with op.batch_alter_table("reports") as batch:
        for name in ("idempotency_key_hash", "tracking_token_hash", "location_captured_at", "location_accuracy_m", "detections_json", "inference_ms", "priority_reason", "model_version"):
            batch.drop_column(name)
