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
4. [DONE] Card enrichment (backend + frontend): priority + due date (labels/
   assignee deferred). AI create/edit can set them. Migration v4.
5. [DONE] Card checklists; docs polish. Each card carries a checklist of items
   that can be added, toggled done, and removed. Migration v5.
6. [DONE] E2E (Playwright) coverage for new flows; coverage review and docs
   refresh (README/AGENTS/PLAN).

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
- Iter 4 [DONE]: card priority + due date, full vertical slice. Migration v4
  adds `cards.priority` (default 'medium') and nullable `cards.due_date`.
  Schemas/DB/routes carry `priority` + `due_date`; AI create/edit ops can set
  them (ai_models). Frontend: `CardMeta` badge, priority select + date input in
  `NewCardForm` and `KanbanCard`, preview badge. Tests: backend
  test_card_fields.py (6); frontend create-with-priority + badge tests.
  Playwright e2e (13) all pass against a real chromium browser.
- Iter 5+6 [DONE]: card checklists, full vertical slice, plus docs refresh.
  Migration v5 adds `card_checklist_items` (id, board_id, card_id, text, done,
  position, created_at) cascading on card and board delete. Schemas add
  `ChecklistItemCreate/Update`, `BoardChecklistItem`, and `checklist` on
  `BoardCard`; `_load_board` attaches each card's checklist. Routes:
  POST/PATCH/DELETE `/api/boards/{id}/cards/{card_id}/checklist[/{item_id}]`,
  scoped by board+card ownership. Frontend: `CardChecklist` component
  (progress, checkboxes, remove, add form), `ChecklistItem` type, grouped
  `ChecklistHandlers` threaded KanbanBoard -> KanbanColumn -> KanbanCard.
  Tests: backend test_checklist.py (9); frontend checklist add/toggle/remove
  unit test; Playwright e2e checklist test (used click() not check() because the
  controlled checkbox reverts until the save round-trips). Docs: README (intro,
  use sections, data shape, file guide), AGENTS (requirements/limitations), and
  PLAN (Phase 8) refreshed to reflect auth + multi-board + card fields +
  checklists. Full suites green: backend 83 passed/1 skipped, frontend 24 unit,
  Playwright 14 e2e. All six plan steps are now DONE.
