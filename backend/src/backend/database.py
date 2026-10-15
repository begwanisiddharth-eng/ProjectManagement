from contextlib import contextmanager
from datetime import UTC, datetime
import sqlite3
import os
from pathlib import Path
from typing import Iterator
from uuid import uuid4

from backend.ai_models import (
    BoardChange,
    CreateCardChange,
    EditCardChange,
    MoveCardChange,
    RenameColumnChange,
)
from backend.auth import USERNAME

ROOT_DIR = Path(__file__).resolve().parents[3]
DEFAULT_DATABASE_PATH = ROOT_DIR / ".data" / "kanban.sqlite3"
SCHEMA_VERSION = 1
DEFAULT_COLUMNS = (
    ("col-backlog", "Backlog"),
    ("col-discovery", "Discovery"),
    ("col-progress", "In Progress"),
    ("col-review", "Review"),
    ("col-done", "Done"),
)
DEFAULT_CARDS = (
    ("card-1", "col-backlog", "Align roadmap themes", "Draft quarterly themes with impact statements and metrics."),
    ("card-2", "col-backlog", "Gather customer signals", "Review support tags, sales notes, and churn feedback."),
    ("card-3", "col-discovery", "Prototype analytics view", "Sketch initial dashboard layout and key drill-downs."),
    ("card-4", "col-progress", "Refine status language", "Standardize column labels and tone across the board."),
    ("card-5", "col-progress", "Design card layout", "Add hierarchy and spacing for scanning dense lists."),
    ("card-6", "col-review", "QA micro-interactions", "Verify hover, focus, and loading states."),
    ("card-7", "col-done", "Ship marketing page", "Final copy approved and asset pack delivered."),
    ("card-8", "col-done", "Close onboarding sprint", "Document release notes and share internally."),
)
MIGRATION_1 = (
    """CREATE TABLE users (
        id TEXT PRIMARY KEY,
        username TEXT NOT NULL UNIQUE,
        created_at TEXT NOT NULL
    )""",
    """CREATE TABLE boards (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
        title TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )""",
    """CREATE TABLE columns (
        id TEXT NOT NULL,
        board_id TEXT NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
        title TEXT NOT NULL CHECK (length(trim(title)) > 0),
        position INTEGER NOT NULL CHECK (position >= 0),
        PRIMARY KEY (board_id, id),
        UNIQUE (board_id, position)
    )""",
    """CREATE TABLE cards (
        id TEXT PRIMARY KEY,
        board_id TEXT NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
        column_id TEXT NOT NULL,
        title TEXT NOT NULL CHECK (length(trim(title)) > 0),
        details TEXT NOT NULL DEFAULT '',
        position INTEGER NOT NULL CHECK (position >= 0),
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE (board_id, column_id, position),
        FOREIGN KEY (board_id, column_id)
            REFERENCES columns(board_id, id) ON DELETE CASCADE
    )""",
)


def timestamp() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class BoardDatabase:
    def __init__(self, path: Path | None = None) -> None:
        configured_path = os.environ.get("KANBAN_DB_PATH")
        self.path = (
            Path(configured_path).expanduser()
            if configured_path and path is None
            else path or DEFAULT_DATABASE_PATH
        )

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL
                )"""
            )
            row = connection.execute(
                "SELECT COALESCE(MAX(version), 0) AS version FROM schema_migrations"
            ).fetchone()
            current_version = int(row["version"])
            if current_version > SCHEMA_VERSION:
                raise RuntimeError(
                    f"Database schema version {current_version} is newer than supported version {SCHEMA_VERSION}."
                )
            if current_version < 1:
                for statement in MIGRATION_1:
                    connection.execute(statement)
                connection.execute(
                    "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                    (1, timestamp()),
                )
            self._seed_mvp_board(connection)

    def _seed_mvp_board(self, connection: sqlite3.Connection) -> None:
        now = timestamp()
        connection.execute(
            "INSERT OR IGNORE INTO users (id, username, created_at) VALUES (?, ?, ?)",
            ("local-user", USERNAME, now),
        )
        user = connection.execute(
            "SELECT id FROM users WHERE username = ?", (USERNAME,)
        ).fetchone()
        if user is None:
            raise RuntimeError("Unable to find the MVP user after initialization.")

        existing_board = connection.execute(
            "SELECT id FROM boards WHERE user_id = ?", (user["id"],)
        ).fetchone()
        if existing_board is not None:
            return

        board_id = str(uuid4())
        connection.execute(
            """INSERT INTO boards (id, user_id, title, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)""",
            (board_id, user["id"], "Kanban Studio", now, now),
        )
        connection.executemany(
            "INSERT INTO columns (id, board_id, title, position) VALUES (?, ?, ?, ?)",
            [
                (column_id, board_id, title, position)
                for position, (column_id, title) in enumerate(DEFAULT_COLUMNS)
            ],
        )
        positions: dict[str, int] = {}
        for card_id, column_id, title, details in DEFAULT_CARDS:
            position = positions.get(column_id, 0)
            connection.execute(
                """INSERT INTO cards
                (id, board_id, column_id, title, details, position, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (card_id, board_id, column_id, title, details, position, now, now),
            )
            positions[column_id] = position + 1

    @staticmethod
    def _board_id(connection: sqlite3.Connection, username: str) -> str | None:
        row = connection.execute(
            """SELECT boards.id FROM boards
            JOIN users ON users.id = boards.user_id
            WHERE users.username = ?""",
            (username,),
        ).fetchone()
        return str(row["id"]) if row is not None else None

    @staticmethod
    def _load_board(connection: sqlite3.Connection, board_id: str) -> dict[str, object]:
        columns = connection.execute(
            "SELECT id, title FROM columns WHERE board_id = ? ORDER BY position",
            (board_id,),
        ).fetchall()
        card_rows = connection.execute(
            """SELECT id, column_id, title, details FROM cards
            WHERE board_id = ? ORDER BY column_id, position""",
            (board_id,),
        ).fetchall()
        cards: dict[str, dict[str, str]] = {}
        card_ids_by_column: dict[str, list[str]] = {
            str(column["id"]): [] for column in columns
        }
        for row in card_rows:
            card_id = str(row["id"])
            column_id = str(row["column_id"])
            cards[card_id] = {
                "id": card_id,
                "title": str(row["title"]),
                "details": str(row["details"]),
            }
            card_ids_by_column[column_id].append(card_id)
        return {
            "columns": [
                {
                    "id": str(column["id"]),
                    "title": str(column["title"]),
                    "cardIds": card_ids_by_column[str(column["id"])],
                }
                for column in columns
            ],
            "cards": cards,
        }

    def get_board(self, username: str) -> dict[str, object] | None:
        with self.connect() as connection:
            board_id = self._board_id(connection, username)
            return self._load_board(connection, board_id) if board_id else None

    def rename_column(
        self, username: str, column_id: str, title: str
    ) -> dict[str, object] | None:
        with self.connect() as connection:
            board_id = self._board_id(connection, username)
            if board_id is None:
                return None
            cursor = connection.execute(
                "UPDATE columns SET title = ? WHERE board_id = ? AND id = ?",
                (title, board_id, column_id),
            )
            return self._load_board(connection, board_id) if cursor.rowcount else None

    def create_card(
        self, username: str, column_id: str, title: str, details: str
    ) -> dict[str, object] | None:
        with self.connect() as connection:
            board_id = self._board_id(connection, username)
            if board_id is None:
                return None
            column = connection.execute(
                "SELECT id FROM columns WHERE board_id = ? AND id = ?",
                (board_id, column_id),
            ).fetchone()
            if column is None:
                return None
            row = connection.execute(
                """SELECT COALESCE(MAX(position), -1) + 1 AS position
                FROM cards WHERE board_id = ? AND column_id = ?""",
                (board_id, column_id),
            ).fetchone()
            now = timestamp()
            connection.execute(
                """INSERT INTO cards
                (id, board_id, column_id, title, details, position, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (str(uuid4()), board_id, column_id, title, details, row["position"], now, now),
            )
            return self._load_board(connection, board_id)

    def update_card(
        self, username: str, card_id: str, title: str, details: str
    ) -> dict[str, object] | None:
        with self.connect() as connection:
            board_id = self._board_id(connection, username)
            if board_id is None:
                return None
            cursor = connection.execute(
                """UPDATE cards SET title = ?, details = ?, updated_at = ?
                WHERE board_id = ? AND id = ?""",
                (title, details, timestamp(), board_id, card_id),
            )
            return self._load_board(connection, board_id) if cursor.rowcount else None

    def delete_card(self, username: str, card_id: str) -> dict[str, object] | None:
        with self.connect() as connection:
            board_id = self._board_id(connection, username)
            if board_id is None:
                return None
            card = connection.execute(
                "SELECT column_id FROM cards WHERE board_id = ? AND id = ?",
                (board_id, card_id),
            ).fetchone()
            if card is None:
                return None
            column_id = str(card["column_id"])
            connection.execute(
                "DELETE FROM cards WHERE board_id = ? AND id = ?", (board_id, card_id)
            )
            self._rewrite_positions(
                connection,
                board_id,
                {column_id: self._card_ids(connection, board_id, column_id)},
            )
            return self._load_board(connection, board_id)

    def move_card(
        self,
        username: str,
        card_id: str,
        column_id: str,
        position: int,
    ) -> dict[str, object] | None:
        with self.connect() as connection:
            board_id = self._board_id(connection, username)
            if board_id is None:
                return None
            if not self._move_card(connection, board_id, card_id, column_id, position):
                return None
            return self._load_board(connection, board_id)

    def apply_ai_changes(
        self, username: str, changes: list[BoardChange]
    ) -> dict[str, object] | None:
        with self.connect() as connection:
            board_id = self._board_id(connection, username)
            if board_id is None:
                return None

            for change in changes:
                if isinstance(change, CreateCardChange):
                    column = connection.execute(
                        "SELECT id FROM columns WHERE board_id = ? AND id = ?",
                        (board_id, change.column_id),
                    ).fetchone()
                    if column is None:
                        raise ValueError("AI change refers to an unknown column.")
                    position = connection.execute(
                        """SELECT COALESCE(MAX(position), -1) + 1 AS position
                        FROM cards WHERE board_id = ? AND column_id = ?""",
                        (board_id, change.column_id),
                    ).fetchone()["position"]
                    now = timestamp()
                    connection.execute(
                        """INSERT INTO cards
                        (id, board_id, column_id, title, details, position, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            str(uuid4()),
                            board_id,
                            change.column_id,
                            change.title,
                            change.details,
                            position,
                            now,
                            now,
                        ),
                    )
                elif isinstance(change, EditCardChange):
                    card = connection.execute(
                        "SELECT title, details FROM cards WHERE board_id = ? AND id = ?",
                        (board_id, change.card_id),
                    ).fetchone()
                    if card is None:
                        raise ValueError("AI change refers to an unknown card.")
                    title = change.title if change.title is not None else card["title"]
                    details = (
                        change.details
                        if change.details is not None
                        else card["details"]
                    )
                    if title != card["title"] or details != card["details"]:
                        connection.execute(
                            """UPDATE cards SET title = ?, details = ?, updated_at = ?
                            WHERE board_id = ? AND id = ?""",
                            (
                                title,
                                details,
                                timestamp(),
                                board_id,
                                change.card_id,
                            ),
                        )
                elif isinstance(change, MoveCardChange):
                    if not self._move_card(
                        connection,
                        board_id,
                        change.card_id,
                        change.column_id,
                        change.position,
                    ):
                        raise ValueError("AI change refers to an unknown card or column.")
                elif isinstance(change, RenameColumnChange):
                    cursor = connection.execute(
                        "UPDATE columns SET title = ? WHERE board_id = ? AND id = ?",
                        (change.title, board_id, change.column_id),
                    )
                    if cursor.rowcount == 0:
                        raise ValueError("AI change refers to an unknown column.")
            return self._load_board(connection, board_id)

    @staticmethod
    def _move_card(
        connection: sqlite3.Connection,
        board_id: str,
        card_id: str,
        column_id: str,
        position: int,
    ) -> bool:
        card = connection.execute(
            "SELECT column_id FROM cards WHERE board_id = ? AND id = ?",
            (board_id, card_id),
        ).fetchone()
        target = connection.execute(
            "SELECT id FROM columns WHERE board_id = ? AND id = ?",
            (board_id, column_id),
        ).fetchone()
        if card is None or target is None:
            return False

        source_column_id = str(card["column_id"])
        source_ids = BoardDatabase._card_ids(connection, board_id, source_column_id)
        source_ids.remove(card_id)
        target_ids = (
            source_ids
            if source_column_id == column_id
            else BoardDatabase._card_ids(connection, board_id, column_id)
        )
        target_ids.insert(min(position, len(target_ids)), card_id)
        positions = {column_id: target_ids}
        if source_column_id != column_id:
            positions[source_column_id] = source_ids
        BoardDatabase._shift_positions(connection, board_id, positions)
        now = timestamp()
        if source_column_id != column_id:
            temporary_position = connection.execute(
                "SELECT COALESCE(MAX(position), -1) + 1 AS position FROM cards WHERE board_id = ?",
                (board_id,),
            ).fetchone()["position"]
            connection.execute(
                """UPDATE cards SET column_id = ?, position = ?, updated_at = ?
                WHERE board_id = ? AND id = ?""",
                (column_id, temporary_position, now, board_id, card_id),
            )
        else:
            connection.execute(
                "UPDATE cards SET updated_at = ? WHERE board_id = ? AND id = ?",
                (now, board_id, card_id),
            )
        BoardDatabase._set_positions(connection, board_id, positions)
        return True

    @staticmethod
    def _card_ids(
        connection: sqlite3.Connection, board_id: str, column_id: str
    ) -> list[str]:
        rows = connection.execute(
            """SELECT id FROM cards
            WHERE board_id = ? AND column_id = ? ORDER BY position""",
            (board_id, column_id),
        ).fetchall()
        return [str(row["id"]) for row in rows]

    @staticmethod
    def _rewrite_positions(
        connection: sqlite3.Connection,
        board_id: str,
        positions: dict[str, list[str]],
    ) -> None:
        BoardDatabase._shift_positions(connection, board_id, positions)
        BoardDatabase._set_positions(connection, board_id, positions)

    @staticmethod
    def _shift_positions(
        connection: sqlite3.Connection,
        board_id: str,
        positions: dict[str, list[str]],
    ) -> None:
        maximum = connection.execute(
            "SELECT COALESCE(MAX(position), 0) AS position FROM cards WHERE board_id = ?",
            (board_id,),
        ).fetchone()["position"]
        offset = int(maximum) + sum(map(len, positions.values())) + 1
        placeholders = ", ".join("?" for _ in positions)
        connection.execute(
            f"UPDATE cards SET position = position + ? WHERE board_id = ? AND column_id IN ({placeholders})",
            (offset, board_id, *positions.keys()),
        )

    @staticmethod
    def _set_positions(
        connection: sqlite3.Connection,
        board_id: str,
        positions: dict[str, list[str]],
    ) -> None:
        for column_id, card_ids in positions.items():
            for position, card_id in enumerate(card_ids):
                connection.execute(
                    "UPDATE cards SET position = ? WHERE board_id = ? AND column_id = ? AND id = ?",
                    (position, board_id, column_id, card_id),
                )
