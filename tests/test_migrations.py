import sqlite3
import importlib.util
from pathlib import Path
from sqlalchemy import inspect


def load_temp_app(tmp_db):
    spec = importlib.util.spec_from_file_location(
        "temp_app", Path(__file__).resolve().parents[1] / "backend" / "app.py"
    )
    module = importlib.util.module_from_spec(spec)
    import os, sys

    prev = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = f"sqlite:///{tmp_db}"
    backend_path = str(Path(__file__).resolve().parents[1] / "backend")
    sys.path.insert(0, backend_path)
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(backend_path)
        if prev is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = prev
    return module


def test_app_auto_adds_capacities_columns(tmp_path):
    db_path = tmp_path / "old.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE api_credentials (id INTEGER PRIMARY KEY, user_id INTEGER, readwise_token TEXT, twos_user_id TEXT, twos_token TEXT, created_at DATETIME, updated_at DATETIME)"
    )
    conn.commit()
    conn.close()

    app_module = load_temp_app(db_path)
    try:
        with app_module.app.app_context():
            inspector = inspect(app_module.db.engine)
            columns = [c["name"] for c in inspector.get_columns("api_credentials")]
            assert "capacities_space_id" in columns
            assert "capacities_token" in columns
            assert "capacities_structure_id" in columns
            assert "capacities_text_property_id" in columns
    finally:
        app_module.scheduler.shutdown(wait=False)
