# Ralph Loop Progress

Task: build Kanban Studio into a comprehensive project-management app with user
management, multiple boards per user, and additional features. Test thoroughly;
keep strong coverage and good integration tests. Branch: `feature/comprehensive-pm`.

Keep the full suite green at the end of every iteration (`uv run --project backend
pytest` and, where frontend changed, `npm run test:unit`). Commit each green
increment so later iterations can build on git history.

## Plan (sequenced)

1. [DONE] User management (backend): password hashing (stdlib pbkdf2), DB-backed
   login, registration endpoint, per-user default board seeding. Migration v2.
2. [DONE] Multiple boards (backend): board CRUD, board-scoped routes
   `/api/boards/{board_id}/...`, ownership checks, migration v3 (drop one-board
   constraint, add board ordering). Refactor DB methods to take board_id.
3. [DONE] Frontend: registration page; board list / switcher / create / rename /
   delete; wire board-scoped API.
4. [ ] Card enrichment (backend + frontend): priority, labels, due date, assignee;
   board search/filter.
5. [ ] Activity/audit, card comments or checklist; polish.
6. [ ] E2E (Playwright) coverage for new flows; coverage review.

## Status log

- Iter 1 [DONE]: user management backend. Added stdlib PBKDF2 password hashing
  (`auth.hash_password`/`verify_password`), migration v2 (`users.password_hash`),
  `BoardDatabase.create_user`/`authenticate`, `/api/auth/register`, DB-backed
  `/api/auth/login`. New users get a seeded empty 5-column board. Default
  `user`/`password` account preserved. Tests: `backend/tests/test_auth.py` (8
  new) + shared `conftest.py` fixture. Suite: 55 passed, 1 skipped.
- Iter 2 [DONE]: multiple boards per user (backend). Migration v3 rebuilds the
  `boards` table to drop `UNIQUE(user_id)` and add `position` (own connection,
  FK off, official ALTER recipe + foreign_key_check). All board/card/column DB
  methods and routes are now board-scoped: `/api/boards`, `/api/boards/{id}`
  (GET/PATCH/DELETE), `/api/boards/{id}/columns/...`, `/api/boards/{id}/cards/...`,
  `/api/boards/{id}/chat`. Ownership via `_owned_board_id`. Cannot delete the
  only board (409). Rewrote test_main.py to the new paths; added test_boards.py
  (10) and test_migrations.py (3, incl. v2->v3 data-preserving rebuild). Suite:
  68 passed, 1 skipped.
- IMPORTANT for next iter: the FRONTEND still calls the old `/api/board*` paths,
  so the app UI and Playwright e2e are currently out of sync with the API.
- Iter 3 [DONE]: frontend. New `BoardBar` (board tabs + create/rename/delete),
  `RegisterForm` + `/register` page, login<->register links. `KanbanBoard` now
  loads `/api/boards`, tracks a current board, and routes every card/column/chat
  call through `/api/boards/{id}/...`; `BoardChat` takes a `boardId`. Rewrote
  `KanbanBoard.test.tsx` (14) for the board-scoped mock + switcher, added
  `RegisterForm.test.tsx` (4). Updated Playwright specs (auth + kanban) to the
  new UI/API and added register + multi-board e2e tests. Frontend: 21 unit tests
  pass, lint clean, `npm run build` exports `/`, `/login`, `/register`.
- NOTE: loop capped at 6 iterations per user request (was 10).
- NOTE: Playwright browser was not cached; installing chromium to run e2e.
- Next (Iter 4): card enrichment (priority/labels/due date) backend + frontend,
  and/or board search; keep coverage strong.
