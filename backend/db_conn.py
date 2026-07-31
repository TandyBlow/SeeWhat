"""
SQLite connection layer for local deployment.
Computes backend dir + DB_PATH once at import, opens row-factory
connections, and the get_db_ctx context manager that commits/rollbacks/closes.
"""
import sqlite3
import os
from contextlib import contextmanager

_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.getenv("DB_PATH", os.path.join(_BACKEND_DIR, "acacia.db"))


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
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
