import pytest
import sqlite3

from db_conn import set_db_path, reset_db_path
from database import init_db


@pytest.fixture(autouse=True)
def isolated_db(tmp_path):
    """Give every test a fresh, isolated SQLite database.

    Redirects db_conn to a per-test temp file (schema initialized) so tests
    never touch the real acacia.db and never depend on import order. The temp
    dir is removed automatically by pytest after the test.
    """
    db_path = tmp_path / "test.db"
    set_db_path(str(db_path))
    init_db()
    yield
    reset_db_path()


@pytest.fixture
def in_memory_db():
    """Create an in-memory SQLite database with the core schema for testing."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    yield conn
    conn.close()


@pytest.fixture
def mock_scope():
    """Minimal ASGI HTTP scope for middleware tests."""
    return {
        "type": "http",
        "method": "GET",
        "path": "/health",
        "headers": [],
        "client": ("10.0.0.1", 54321),
    }


@pytest.fixture
def mock_receive():
    """No-op ASGI receive callable."""
    async def _receive():
        return {"type": "http.request", "body": b""}
    return _receive


@pytest.fixture
def mock_send():
    """ASGI send callable that captures response status and body."""
    class SendCollector:
        def __init__(self):
            self.status = 0
            self.body = b""
            self.headers = []
            self.messages = []

        async def __call__(self, message):
            self.messages.append(message)
            if message["type"] == "http.response.start":
                self.status = message["status"]
                self.headers = message.get("headers", [])
            elif message["type"] == "http.response.body":
                self.body += message.get("body", b"")

    collector = SendCollector()
    return collector
