# SQLite data model proposal

The proposed schema is in [kanban-schema.json](./kanban-schema.json). This is a design artifact, not a live database or migration.

## Ownership and board structure

- `users` stores the local user identity. The MVP account is seeded as `local-user` / `user`; its hardcoded password is not stored in SQLite.
- `boards.user_id` is unique, enforcing one board per user.
- `columns` belong to a board. Their IDs are stable identifiers for the fixed board stages; renaming a stage updates its title, not its ID.
- The five fixed column IDs and initial titles are listed in `kanban-schema.json`. The API permits renaming titles only; adding, removing, or reordering columns is not supported.
- `cards` belong to a board and a column. The composite foreign key `(board_id, column_id)` ensures a card cannot refer to a column from another user's board.
- Position fields order columns and cards. Database constraints prevent negative positions and duplicate positions within their respective scopes.
- Deleting a user cascades through that user's board, columns, and cards.

## Initialization and persistence

The application creates the SQLite database in an ignored, project-local data directory when it is absent. Tests use separate temporary database paths. Foreign-key enforcement is enabled for each connection. Ordered schema migrations are recorded and applied transactionally, without dropping or replacing existing user data.

On initial setup, seed the MVP user, their single board, the five existing fixed columns, and the eight existing demo cards from `frontend/src/lib/kanban.ts`. SQLite stores timestamps as UTC ISO 8601 text. The runtime path is `.data/kanban.sqlite3`, overridable with `KANBAN_DB_PATH`; the database file is runtime data and is not committed. The JSON remains the reviewed schema proposal, and `backend/src/backend/database.py` contains the runtime migration and persistence implementation.

## Approval

The user approved the proposed entities, uniqueness and ownership constraints, initial board contents, and database initialization approach before Phase 6 implementation.
