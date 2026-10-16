from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.main import create_app


@pytest.fixture
def client(tmp_path: Path):
    frontend_dir = tmp_path / "frontend"
    frontend_dir.mkdir()
    (frontend_dir / "index.html").write_text(
        "<h1>Kanban Studio</h1>", encoding="utf-8"
    )
    login_dir = frontend_dir / "login"
    login_dir.mkdir()
    (login_dir / "index.html").write_text("<h1>Sign in</h1>", encoding="utf-8")
    app = create_app(
        frontend_dir=frontend_dir,
        database_path=tmp_path / ".data" / "kanban.sqlite3",
    )
    with TestClient(app) as test_client:
        yield test_client
