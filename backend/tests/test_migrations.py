from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


def test_upgrade_existing_sqlite_schema(tmp_path):
    database = tmp_path / "legacy.sqlite3"
    engine = create_engine(f"sqlite:///{database.as_posix()}")
    with engine.begin() as connection:
        connection.execute(text("""CREATE TABLE reports (
            id INTEGER PRIMARY KEY, title VARCHAR(140) NOT NULL, description TEXT NOT NULL,
            category VARCHAR(40) NOT NULL, status VARCHAR(30) NOT NULL, priority VARCHAR(20) NOT NULL,
            confidence FLOAT, latitude FLOAT, longitude FLOAT, image_path VARCHAR(500),
            image_name VARCHAR(255), detector_mode VARCHAR(30) NOT NULL,
            created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL)"""))
        connection.execute(text("INSERT INTO reports (id,title,description,category,status,priority,detector_mode,created_at,updated_at) VALUES (5,'preserved report','','unknown','pending_review','review','demo','2026-01-01','2026-01-01')"))
        connection.execute(text("""CREATE TABLE status_events (
            id INTEGER PRIMARY KEY, report_id INTEGER NOT NULL, old_status VARCHAR(30),
            new_status VARCHAR(30) NOT NULL, note TEXT NOT NULL, created_at DATETIME NOT NULL)"""))
    engine.dispose()

    backend = __import__("pathlib").Path(__file__).resolve().parents[1]
    config = Config(str(backend / "alembic.ini"))
    config.set_main_option("script_location", str(backend / "migrations"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database.as_posix()}")
    command.upgrade(config, "head")

    upgraded = create_engine(f"sqlite:///{database.as_posix()}")
    assert {"tracking_token_hash", "idempotency_key_hash", "detections_json", "location_captured_at", "priority_reason", "assigned_team", "assigned_at", "assigned_by"} <= {column["name"] for column in inspect(upgraded).get_columns("reports")}
    assert "resolution_evidence" in inspect(upgraded).get_table_names()
    assert "actor" in {column["name"] for column in inspect(upgraded).get_columns("status_events")}
    with upgraded.connect() as connection:
        assert connection.execute(text("SELECT title FROM reports WHERE id=5")).scalar_one() == "preserved report"
    assert {index["name"] for index in inspect(upgraded).get_indexes("reports")} >= {"ix_reports_tracking_token_hash", "ix_reports_idempotency_key_hash"}
    upgraded.dispose()
