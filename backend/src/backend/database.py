import os
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
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
from backend.auth import PASSWORD, USERNAME, hash_password, verify_password

ROOT_DIR = Path(__file__).resolve().parents[3]
DEFAULT_DATABASE_PATH = ROOT_DIR / ".data" / "kanban.sqlite3"
SCHEMA_VERSION = 5
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
MIGRATION_2 = (
    "ALTER TABLE users ADD COLUMN password_hash TEXT NOT NULL DEFAULT ''",
)
MIGRATION_4 = (
    "ALTER TABLE cards ADD COLUMN priority TEXT NOT NULL DEFAULT 'medium'",
    "ALTER TABLE cards ADD COLUMN due_date TEXT",
)
MIGRATION_5 = (
    """CREATE TABLE card_checklist_items (
        id TEXT PRIMARY KEY,
        board_id TEXT NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
        card_id TEXT NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
        text TEXT NOT NULL CHECK (length(trim(text)) > 0),
        done INTEGER NOT NULL DEFAULT 0 CHECK (done IN (0, 1)),
        position INTEGER NOT NULL CHECK (position >= 0),
        created_at TEXT NOT NULL
    )""",
)
MIGRATION_3 = (
    """CREATE TABLE boards_v3 (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        title TEXT NOT NULL,
        position INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )""",
    """INSERT INTO boards_v3 (id, user_id, title, position, created_at, updated_at)
        SELECT id, user_id, title, 0, created_at, updated_at FROM boards""",
    "DROP TABLE boards",
    "ALTER TABLE boards_v3 RENAME TO boards",
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
        current_version = self._current_version()
        if current_version > SCHEMA_VERSION:
            raise RuntimeError(
                f"Database schema version {current_version} is newer than supported version {SCHEMA_VERSION}."
            )
        if current_version < 1:
            self._apply_migration(1, MIGRATION_1)
        if current_version < 2:
            self._apply_migration(2, MIGRATION_2)
        if current_version < 3:
            self._apply_migration_3()
        if current_version < 4:
            self._apply_migration(4, MIGRATION_4)
        if current_version < 5:
            self._apply_migration(5, MIGRATION_5)
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._seed_mvp_board(connection)

    def _current_version(self) -> int:
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
            return int(row["version"])

    def _apply_migration(self, version: int, statements: tuple[str, ...]) -> None:
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            for statement in statements:
                connection.execute(statement)
            connection.execute(
                "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                (version, timestamp()),
            )

    def _apply_migration_3(self) -> None:
        """Drop the one-board-per-user UNIQUE constraint and add board ordering.

        Rebuilding a table referenced by foreign keys needs foreign_keys OFF,
        which SQLite only honors outside a transaction, so this runs on its own
        connection following the official ALTER TABLE recipe.
        """
        connection = sqlite3.connect(self.path, timeout=5)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA foreign_keys = OFF")
            connection.execute("BEGIN IMMEDIATE")
            for statement in MIGRATION_3:
                connection.execute(statement)
            connection.execute(
                "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                (3, timestamp()),
            )
            violations = connection.execute("PRAGMA foreign_key_check").fetchall()
            if violations:
                raise RuntimeError("Migration 3 left dangling foreign keys.")
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _seed_mvp_board(self, connection: sqlite3.Connection) -> None:
        now = timestamp()
        connection.execute(
            """INSERT OR IGNORE INTO users (id, username, password_hash, created_at)
            VALUES (?, ?, ?, ?)""",
            ("local-user", USERNAME, hash_password(PASSWORD), now),
        )
        user = connection.execute(
            "SELECT id, password_hash FROM users WHERE username = ?", (USERNAME,)
        ).fetchone()
        if user is None:
            raise RuntimeError("Unable to find the MVP user after initialization.")
        if not user["password_hash"]:
            connection.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (hash_password(PASSWORD), user["id"]),
            )

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
        self._seed_columns(connection, board_id)
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
    def _seed_columns(connection: sqlite3.Connection, board_id: str) -> None:
        connection.executemany(
            "INSERT INTO columns (id, board_id, title, position) VALUES (?, ?, ?, ?)",
            [
                (column_id, board_id, title, position)
                for position, (column_id, title) in enumerate(DEFAULT_COLUMNS)
            ],
        )

    def create_user(self, username: str, password: str) -> str | None:
        """Create a user with a seeded default board. Return the id, or None if taken."""
        with self.connect() as connection:
            existing = connection.execute(
                "SELECT id FROM users WHERE username = ?", (username,)
            ).fetchone()
            if existing is not None:
                return None
            now = timestamp()
            user_id = str(uuid4())
            connection.execute(
                """INSERT INTO users (id, username, password_hash, created_at)
                VALUES (?, ?, ?, ?)""",
                (user_id, username, hash_password(password), now),
            )
            board_id = str(uuid4())
            connection.execute(
                """INSERT INTO boards (id, user_id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)""",
                (board_id, user_id, "My Board", now, now),
            )
            self._seed_columns(connection, board_id)
            return user_id

    def authenticate(self, username: str, password: str) -> bool:
        """Return True when the username exists and the password matches its hash."""
        with self.connect() as connection:
            row = connection.execute(
                "SELECT password_hash FROM users WHERE username = ?", (username,)
            ).fetchone()
        return row is not None and verify_password(password, row["password_hash"])

    @staticmethod
    def _owned_board_id(
        connection: sqlite3.Connection, username: str, board_id: str
    ) -> str | None:
        row = connection.execute(
            """SELECT boards.id FROM boards
            JOIN users ON users.id = boards.user_id
            WHERE users.username = ? AND boards.id = ?""",
            (username, board_id),
        ).fetchone()
        return str(row["id"]) if row is not None else None

    @staticmethod
    def _board_summary(row: sqlite3.Row) -> dict[str, str]:
        return {
            "id": str(row["id"]),
            "title": str(row["title"]),
            "createdAt": str(row["created_at"]),
            "updatedAt": str(row["updated_at"]),
        }

    def list_boards(self, username: str) -> list[dict[str, str]]:
        with self.connect() as connection:
            rows = connection.execute(
                """SELECT boards.id, boards.title, boards.created_at, boards.updated_at
                FROM boards JOIN users ON users.id = boards.user_id
                WHERE users.username = ?
                ORDER BY boards.position, boards.created_at""",
                (username,),
            ).fetchall()
            return [self._board_summary(row) for row in rows]

    def create_board(self, username: str, title: str) -> dict[str, str] | None:
        with self.connect() as connection:
            user = connection.execute(
                "SELECT id FROM users WHERE username = ?", (username,)
            ).fetchone()
            if user is None:
                return None
            position = connection.execute(
                "SELECT COALESCE(MAX(position), -1) + 1 AS position FROM boards WHERE user_id = ?",
                (user["id"],),
            ).fetchone()["position"]
            now = timestamp()
            board_id = str(uuid4())
            connection.execute(
                """INSERT INTO boards (id, user_id, title, position, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (board_id, user["id"], title, position, now, now),
            )
            self._seed_columns(connection, board_id)
            row = connection.execute(
                "SELECT id, title, created_at, updated_at FROM boards WHERE id = ?",
                (board_id,),
            ).fetchone()
            return self._board_summary(row)

    def rename_board(
        self, username: str, board_id: str, title: str
    ) -> dict[str, str] | None:
        with self.connect() as connection:
            if self._owned_board_id(connection, username, board_id) is None:
                return None
            connection.execute(
                "UPDATE boards SET title = ?, updated_at = ? WHERE id = ?",
                (title, timestamp(), board_id),
            )
            row = connection.execute(
                "SELECT id, title, created_at, updated_at FROM boards WHERE id = ?",
                (board_id,),
            ).fetchone()
            return self._board_summary(row)

    def delete_board(self, username: str, board_id: str) -> str:
        """Delete a board. Return 'deleted', 'not_found', or 'last_board'."""
        with self.connect() as connection:
            user = connection.execute(
                "SELECT id FROM users WHERE username = ?", (username,)
            ).fetchone()
            if user is None:
                return "not_found"
            if self._owned_board_id(connection, username, board_id) is None:
                return "not_found"
            count = connection.execute(
                "SELECT COUNT(*) AS count FROM boards WHERE user_id = ?",
                (user["id"],),
            ).fetchone()["count"]
            if count <= 1:
                return "last_board"
            connection.execute("DELETE FROM boards WHERE id = ?", (board_id,))
            return "deleted"

    @staticmethod
    def _load_board(connection: sqlite3.Connection, board_id: str) -> dict[str, object]:
        columns = connection.execute(
            "SELECT id, title FROM columns WHERE board_id = ? ORDER BY position",
            (board_id,),
        ).fetchall()
        card_rows = connection.execute(
            """SELECT id, column_id, title, details, priority, due_date FROM cards
            WHERE board_id = ? ORDER BY column_id, position""",
            (board_id,),
        ).fetchall()
        checklist_rows = connection.execute(
            """SELECT id, card_id, text, done FROM card_checklist_items
            WHERE board_id = ? ORDER BY card_id, position""",
            (board_id,),
        ).fetchall()
        checklist_by_card: dict[str, list[dict[str, object]]] = {}
        for row in checklist_rows:
            checklist_by_card.setdefault(str(row["card_id"]), []).append(
                {
                    "id": str(row["id"]),
                    "text": str(row["text"]),
                    "done": bool(row["done"]),
                }
            )
        cards: dict[str, dict[str, object]] = {}
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
                "priority": str(row["priority"]),
                "dueDate": row["due_date"],
                "checklist": checklist_by_card.get(card_id, []),
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

    def get_board(self, username: str, board_id: str) -> dict[str, object] | None:
        with self.connect() as connection:
            if self._owned_board_id(connection, username, board_id) is None:
                return None
            return self._load_board(connection, board_id)

    def rename_column(
        self, username: str, board_id: str, column_id: str, title: str
    ) -> dict[str, object] | None:
        with self.connect() as connection:
            if self._owned_board_id(connection, username, board_id) is None:
                return None
            cursor = connection.execute(
                "UPDATE columns SET title = ? WHERE board_id = ? AND id = ?",
                (title, board_id, column_id),
            )
            return self._load_board(connection, board_id) if cursor.rowcount else None

    def create_card(
        self,
        username: str,
        board_id: str,
        column_id: str,
        title: str,
        details: str,
        priority: str = "medium",
        due_date: str | None = None,
    ) -> dict[str, object] | None:
        with self.connect() as connection:
            if self._owned_board_id(connection, username, board_id) is None:
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
                (id, board_id, column_id, title, details, priority, due_date,
                 position, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    str(uuid4()),
                    board_id,
                    column_id,
                    title,
                    details,
                    priority,
                    due_date,
                    row["position"],
                    now,
                    now,
                ),
            )
            return self._load_board(connection, board_id)

    def update_card(
        self,
        username: str,
        board_id: str,
        card_id: str,
        title: str,
        details: str,
        priority: str = "medium",
        due_date: str | None = None,
    ) -> dict[str, object] | None:
        with self.connect() as connection:
            if self._owned_board_id(connection, username, board_id) is None:
                return None
            cursor = connection.execute(
                """UPDATE cards
                SET title = ?, details = ?, priority = ?, due_date = ?, updated_at = ?
                WHERE board_id = ? AND id = ?""",
                (title, details, priority, due_date, timestamp(), board_id, card_id),
            )
            return self._load_board(connection, board_id) if cursor.rowcount else None

    def delete_card(
        self, username: str, board_id: str, card_id: str
    ) -> dict[str, object] | None:
        with self.connect() as connection:
            if self._owned_board_id(connection, username, board_id) is None:
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

    @staticmethod
    def _owned_card_id(
        connection: sqlite3.Connection, board_id: str, card_id: str
    ) -> str | None:
        row = connection.execute(
            "SELECT id FROM cards WHERE board_id = ? AND id = ?",
            (board_id, card_id),
        ).fetchone()
        return str(row["id"]) if row is not None else None

    def add_checklist_item(
        self, username: str, board_id: str, card_id: str, text: str
    ) -> dict[str, object] | None:
        with self.connect() as connection:
            if self._owned_board_id(connection, username, board_id) is None:
                return None
            if self._owned_card_id(connection, board_id, card_id) is None:
                return None
            position = connection.execute(
                """SELECT COALESCE(MAX(position), -1) + 1 AS position
                FROM card_checklist_items WHERE card_id = ?""",
                (card_id,),
            ).fetchone()["position"]
            connection.execute(
                """INSERT INTO card_checklist_items
                (id, board_id, card_id, text, done, position, created_at)
                VALUES (?, ?, ?, ?, 0, ?, ?)""",
                (str(uuid4()), board_id, card_id, text, position, timestamp()),
            )
            return self._load_board(connection, board_id)

    def set_checklist_item(
        self, username: str, board_id: str, card_id: str, item_id: str, done: bool
    ) -> dict[str, object] | None:
        with self.connect() as connection:
            if self._owned_board_id(connection, username, board_id) is None:
                return None
            cursor = connection.execute(
                """UPDATE card_checklist_items SET done = ?
                WHERE board_id = ? AND card_id = ? AND id = ?""",
                (int(done), board_id, card_id, item_id),
            )
            return self._load_board(connection, board_id) if cursor.rowcount else None

    def delete_checklist_item(
        self, username: str, board_id: str, card_id: str, item_id: str
    ) -> dict[str, object] | None:
        with self.connect() as connection:
            if self._owned_board_id(connection, username, board_id) is None:
                return None
            cursor = connection.execute(
                """DELETE FROM card_checklist_items
                WHERE board_id = ? AND card_id = ? AND id = ?""",
                (board_id, card_id, item_id),
            )
            return self._load_board(connection, board_id) if cursor.rowcount else None

    def move_card(
        self,
        username: str,
        board_id: str,
        card_id: str,
        column_id: str,
        position: int,
    ) -> dict[str, object] | None:
        with self.connect() as connection:
            if self._owned_board_id(connection, username, board_id) is None:
                return None
            if not self._move_card(connection, board_id, card_id, column_id, position):
                return None
            return self._load_board(connection, board_id)

    def apply_ai_changes(
        self, username: str, board_id: str, changes: list[BoardChange]
    ) -> dict[str, object] | None:
        with self.connect() as connection:
            if self._owned_board_id(connection, username, board_id) is None:
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
                        (id, board_id, column_id, title, details, priority, due_date,
                         position, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            str(uuid4()),
                            board_id,
                            change.column_id,
                            change.title,
                            change.details,
                            change.priority,
                            change.due_date,
                            position,
                            now,
                            now,
                        ),
                    )
                elif isinstance(change, EditCardChange):
                    card = connection.execute(
                        """SELECT title, details, priority, due_date
                        FROM cards WHERE board_id = ? AND id = ?""",
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
                    priority = (
                        change.priority
                        if change.priority is not None
                        else card["priority"]
                    )
                    due_date = (
                        change.due_date
                        if change.due_date is not None
                        else card["due_date"]
                    )
                    if (
                        title != card["title"]
                        or details != card["details"]
                        or priority != card["priority"]
                        or due_date != card["due_date"]
                    ):
                        connection.execute(
                            """UPDATE cards
                            SET title = ?, details = ?, priority = ?, due_date = ?,
                                updated_at = ?
                            WHERE board_id = ? AND id = ?""",
                            (
                                title,
                                details,
                                priority,
                                due_date,
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
