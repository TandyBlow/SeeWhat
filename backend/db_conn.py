"""
SQLite connection layer for local deployment.
Computes backend dir + default DB path at import, opens row-factory
connections, and the get_db_ctx context manager that commits/rollbacks/closes.

Tests can redirect every connection to an isolated database via set_db_path()
so the real acacia.db is never touched and isolation does not depend on import
order or environment-variable timing.
"""
import sqlite3
import os
from contextlib import contextmanager

_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.getenv("DB_PATH", os.path.join(_BACKEND_DIR, "acacia.db"))

# Test override: when set, get_db()/get_db_ctx() connect here instead of DB_PATH.
_test_db_path: str | None = None


def set_db_path(path: str) -> None:
    """Redirect the app's SQLite connections to an isolated database (tests)."""
    global _test_db_path
    _test_db_path = path


def reset_db_path() -> None:
    """Restore connections to the default DB_PATH."""
    global _test_db_path
    _test_db_path = None


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(_test_db_path or DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_db_ctx():
    conn = get_db()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
