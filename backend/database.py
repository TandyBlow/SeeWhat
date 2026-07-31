"""
SQLite persistence layer for local deployment.
Split into db_conn (connection layer) and db_init (schema bootstrap).
"""
from db_conn import get_db_ctx, get_db, DB_PATH, _BACKEND_DIR
from db_init import init_db
