"""Schema migration behavior, including the board table rebuild in v3."""

import sqlite3
from pathlib import Path

import pytest

from backend.database import (
    MIGRATION_1,
    MIGRATION_2,
    SCHEMA_VERSION,
    BoardDatabase,
    timestamp,
)


def _build_legacy_v2_database(path: Path) -> None:
    """Create a version-2 database (one board per user) with real data."""
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA foreign_keys = ON")
    now = timestamp()
    try:
        connection.execute(
            """CREATE TABLE schema_migrations (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL
            )"""
        )
        for statement in MIGRATION_1:
            connection.execute(statement)
        for statement in MIGRATION_2:
            connection.execute(statement)
        connection.executemany(
            "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
            [(1, now), (2, now)],
        )
        connection.execute(
            """INSERT INTO users (id, username, password_hash, created_at)
            VALUES (?, ?, ?, ?)""",
            ("legacy-user", "legacy", "", now),
        )
        connection.execute(
            """INSERT INTO boards (id, user_id, title, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)""",
            ("legacy-board", "legacy-user", "Legacy Board", now, now),
        )
        connection.execute(
            "INSERT INTO columns (id, board_id, title, position) VALUES (?, ?, ?, ?)",
            ("col-backlog", "legacy-board", "Backlog", 0),
        )
        connection.execute(
            """INSERT INTO cards
            (id, board_id, column_id, title, details, position, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            ("legacy-card", "legacy-board", "col-backlog", "Keep me", "", 0, now, now),
        )
        connection.commit()
    finally:
        connection.close()


def test_v3_migration_preserves_data_and_drops_one_board_constraint(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / ".data" / "kanban.sqlite3"
    _build_legacy_v2_database(db_path)
    database = BoardDatabase(db_path)

    database.initialize()

    # Legacy data survived the boards table rebuild.
    board = database.get_board("legacy", "legacy-board")
    assert board is not None
    assert any(card["title"] == "Keep me" for card in board["cards"].values())

    # Schema is now fully migrated and the board position column exists.
    with database.connect() as connection:
        version = connection.execute(
            "SELECT MAX(version) AS version FROM schema_migrations"
        ).fetchone()["version"]
        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(boards)").fetchall()
        }
    assert version == SCHEMA_VERSION
    assert "position" in columns

    # The one-board-per-user UNIQUE constraint is gone: a second board is allowed.
    second = database.create_board("legacy", "Second Board")
    assert second is not None
    assert len(database.list_boards("legacy")) == 2


def test_migration_is_idempotent_across_repeated_initialize(tmp_path: Path) -> None:
    db_path = tmp_path / ".data" / "kanban.sqlite3"
    database = BoardDatabase(db_path)

    database.initialize()
    database.initialize()

    with database.connect() as connection:
        count = connection.execute(
            "SELECT COUNT(*) AS count FROM schema_migrations"
        ).fetchone()["count"]
    assert count == SCHEMA_VERSION


def test_initialize_rejects_a_future_schema_version(tmp_path: Path) -> None:
    db_path = tmp_path / ".data" / "kanban.sqlite3"
    database = BoardDatabase(db_path)
    database.initialize()
    with database.connect() as connection:
        connection.execute(
            "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
            (SCHEMA_VERSION + 1, timestamp()),
        )

    with pytest.raises(RuntimeError, match="newer than supported"):
        database.initialize()
